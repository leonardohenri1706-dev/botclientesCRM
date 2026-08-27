from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from uuid import UUID


class BusinessLocation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_meters: int = Field(default=1000, ge=100, le=50000)


class ScrapingRequest(BaseModel):
    campaign_id: UUID
    location: BusinessLocation
    categories: List[str] = Field(default=["restaurant", "store", "health", "beauty"])
    max_results: int = Field(default=100, ge=1, le=500)


class ScrapedBusiness(BaseModel):
    place_id: str
    business_name: str
    phone_number: Optional[str] = None
    address: str
    latitude: float
    longitude: float
    category: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    website: Optional[HttpUrl] = None
    has_competitor_infrastructure: bool = False


class ScrapingResponse(BaseModel):
    campaign_id: UUID
    total_found: int
    businesses: List[ScrapedBusiness]
    filtered_count: int
    qualified_leads: List[ScrapedBusiness]