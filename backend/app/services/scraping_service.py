import httpx
import asyncio
from typing import List, Optional
from uuid import UUID
from schemas.scraping import ScrapingRequest, ScrapedBusiness, ScrapingResponse, BusinessLocation
from schemas.lead import LeadCreate
from config.settings import get_settings
from config.database import execute, fetchrow
import random


class GoogleMapsScraper:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_nearby(
        self,
        location: BusinessLocation,
        keyword: str,
        max_results: int = 20
    ) -> List[ScrapedBusiness]:
        url = f"{self.base_url}/nearbysearch/json"
        params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": location.radius_meters,
            "keyword": keyword,
            "key": self.settings.GOOGLE_MAPS_API_KEY,
        }

        results = []
        next_page_token = None

        while len(results) < max_results:
            if next_page_token:
                params["pagetoken"] = next_page_token
                await asyncio.sleep(2)

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK" and data.get("status") != "ZERO_RESULTS":
                raise Exception(f"Google Maps API error: {data.get('status')} - {data.get('error_message', '')}")

            for place in data.get("results", []):
                if len(results) >= max_results:
                    break

                business = await self._parse_place(place)
                if business:
                    results.append(business)

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

        return results[:max_results]

    async def _parse_place(self, place: dict) -> Optional[ScrapedBusiness]:
        place_id = place.get("place_id")
        if not place_id:
            return None

        details = await self.get_place_details(place_id)
        if not details:
            return None

        phone = details.get("formatted_phone_number") or details.get("international_phone_number")
        website = details.get("website")

        return ScrapedBusiness(
            place_id=place_id,
            business_name=place.get("name", ""),
            phone_number=phone,
            address=details.get("formatted_address", place.get("vicinity", "")),
            latitude=place["geometry"]["location"]["lat"],
            longitude=place["geometry"]["location"]["lng"],
            category=place.get("types", [""])[0],
            rating=place.get("rating"),
            user_ratings_total=place.get("user_ratings_total"),
            website=website,
            has_competitor_infrastructure=False
        )

    async def get_place_details(self, place_id: str) -> Optional[dict]:
        url = f"{self.base_url}/details/json"
        params = {
            "place_id": place_id,
            "fields": "formatted_phone_number,international_phone_number,formatted_address,website,type",
            "key": self.settings.GOOGLE_MAPS_API_KEY,
        }

        response = await self.client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            return data.get("result")
        return None

    async def close(self):
        await self.client.aclose()


class ScrapingService:
    def __init__(self):
        self.scraper = GoogleMapsScraper()

    async def execute_scraping(self, request: ScrapingRequest) -> ScrapingResponse:
        all_businesses = []

        for category in request.categories:
            businesses = await self.scraper.search_nearby(
                request.location,
                category,
                max_results=request.max_results // len(request.categories) + 1
            )
            all_businesses.extend(businesses)

        qualified = await self._apply_qualification_filters(all_businesses, request.campaign_id)
        saved_leads = await self._save_leads(qualified, request.campaign_id)

        return ScrapingResponse(
            campaign_id=request.campaign_id,
            total_found=len(all_businesses),
            businesses=all_businesses,
            filtered_count=len(all_businesses) - len(qualified),
            qualified_leads=saved_leads
        )

    async def _apply_qualification_filters(
        self,
        businesses: List[ScrapedBusiness],
        campaign_id: UUID
    ) -> List[ScrapedBusiness]:
        qualified = []

        for biz in businesses:
            if not biz.phone_number:
                continue

            normalized_phone = self._normalize_phone_e164(biz.phone_number)
            if not normalized_phone:
                continue
            biz.phone_number = normalized_phone

            biz.has_competitor_infrastructure = await self._check_competitor_infrastructure(biz)
            if biz.has_competitor_infrastructure:
                continue

            qualified.append(biz)

        return qualified

    def _normalize_phone_e164(self, phone: str) -> Optional[str]:
        import re
        digits = re.sub(r"\D", "", phone)

        if digits.startswith("55"):
            digits = digits[2:]
        if len(digits) == 10 or len(digits) == 11:
            digits = "55" + digits
        elif not digits.startswith("55"):
            digits = "55" + digits

        if re.match(r"^\+?[1-9]\d{1,14}$", digits):
            return f"+{digits}" if not digits.startswith("+") else digits

        return None

    async def _check_competitor_infrastructure(self, business: ScrapedBusiness) -> bool:
        if business.website:
            pass
        return False

    async def _save_leads(
        self,
        businesses: List[ScrapedBusiness],
        campaign_id: UUID
    ) -> List[ScrapedBusiness]:
        saved = []

        for biz in businesses:
            lead_data = LeadCreate(
                campaign_id=campaign_id,
                business_name=biz.business_name,
                phone_number=biz.phone_number,
                preview_url=str(biz.website) if biz.website else None
            )

            try:
                await execute("""
                    INSERT INTO leads (campaign_id, business_name, phone_number, preview_url, status, calls_count)
                    VALUES ($1, $2, $3, $4, 'NOVO', 0)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, lead_data.campaign_id, lead_data.business_name, lead_data.phone_number, lead_data.preview_url)
                saved.append(biz)
            except Exception as e:
                print(f"Error saving lead {biz.business_name}: {e}")

        return saved

    async def close(self):
        await self.scraper.close()