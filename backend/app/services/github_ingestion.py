import httpx
import base64
import json
from typing import List, Optional, Dict, Any
from uuid import UUID
from schemas.campaign import AIRules
from config.settings import get_settings
from config.database import execute, fetchrow


class GitHubIngestionService:
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"token {self.settings.GITHUB_TOKEN}" if self.settings.GITHUB_TOKEN else None,
                "Accept": "application/vnd.github.v3+json"
            }
        )

    async def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        owner, repo = self._parse_repo_url(repo_url)
        if not owner or not repo:
            raise ValueError("Invalid GitHub repository URL")

        strategic_files = await self._fetch_strategic_files(owner, repo)
        analysis = self._analyze_files(strategic_files)

        return {
            "repository": f"{owner}/{repo}",
            "files_analyzed": list(strategic_files.keys()),
            "icp_profile": analysis.get("icp_profile", {}),
            "objection_args": analysis.get("objection_args", []),
            "pricing_signals": analysis.get("pricing_signals", {}),
            "tech_stack": analysis.get("tech_stack", []),
            "target_market": analysis.get("target_market", "")
        }

    def _parse_repo_url(self, url: str) -> tuple[Optional[str], Optional[str]]:
        import re
        patterns = [
            r"github\.com[:/]([^/]+)/([^/\.]+)",
            r"github\.com/([^/]+)/([^/\.]+)"
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2).replace(".git", "")
        return None, None

    async def _fetch_strategic_files(self, owner: str, repo: str) -> Dict[str, str]:
        strategic_paths = [
            "README.md", "readme.md", "Readme.md",
            "package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod",
            "pricing.md", "PRICING.md", "pricing.txt",
            "business-model.md", "BUSINESS_MODEL.md",
            "ICP.md", "icp.md", "ideal-customer.md",
            "sales.md", "SALES.md", "pitch.md",
            "docs/pricing.md", "docs/icp.md", "docs/sales.md",
            "marketing/strategy.md", "strategy.md",
            ".github/COPILOT.md", "AGENTS.md", "CLAUDE.md"
        ]

        files = {}
        for path in strategic_paths:
            try:
                content = await self._get_file_content(owner, repo, path)
                if content:
                    files[path] = content
            except Exception:
                continue

        try:
            tree = await self._get_repo_tree(owner, repo)
            for item in tree.get("tree", []):
                if item["type"] == "blob" and item["path"].endswith(".md"):
                    if item["path"] not in files and len(files) < 20:
                        content = await self._get_file_content(owner, repo, item["path"])
                        if content:
                            files[item["path"]] = content
        except Exception:
            pass

        return files

    async def _get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        response = await self.client.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return None

    async def _get_repo_tree(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        response = await self.client.get(url)
        if response.status_code == 404:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
            response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    def _analyze_files(self, files: Dict[str, str]) -> Dict[str, Any]:
        combined_content = "\n\n".join([f"=== {path} ===\n{content}" for path, content in files.items()])

        analysis = {
            "icp_profile": self._extract_icp_signals(combined_content),
            "objection_args": self._extract_objection_args(combined_content),
            "pricing_signals": self._extract_pricing_signals(combined_content),
            "tech_stack": self._extract_tech_stack(combined_content, files),
            "target_market": self._extract_target_market(combined_content)
        }

        return analysis

    def _extract_icp_signals(self, content: str) -> Dict[str, Any]:
        import re
        signals = {
            "company_size": None,
            "industry": [],
            "pain_points": [],
            "tech_maturity": "unknown",
            "budget_range": None
        }

        content_lower = content.lower()

        if any(kw in content_lower for kw in ["enterprise", "large company", "fortune 500", "1000+ employees"]):
            signals["company_size"] = "enterprise"
        elif any(kw in content_lower for kw in ["mid-market", "mid market", "100-1000", "scaling startup"]):
            signals["company_size"] = "mid_market"
        elif any(kw in content_lower for kw in ["small business", "smb", "startup", "1-50", "50-100"]):
            signals["company_size"] = "smb"

        industries = {
            "saas": ["saas", "software as a service", "subscription"],
            "ecommerce": ["ecommerce", "e-commerce", "shopify", "online store"],
            "fintech": ["fintech", "financial", "payments", "banking"],
            "healthtech": ["healthtech", "healthcare", "medical", "hipaa"],
            "edtech": ["edtech", "education", "learning", "lms"],
            "real_estate": ["real estate", "property", "realtor", "mls"],
            "restaurant": ["restaurant", "food delivery", "pos system"],
            "agency": ["agency", "marketing agency", "digital agency", "clients"]
        }
        for industry, keywords in industries.items():
            if any(kw in content_lower for kw in keywords):
                signals["industry"].append(industry)

        pain_keywords = {
            "manual_process": ["manual", "spreadsheet", "excel", "time-consuming"],
            "no_automation": ["automat", "no automation", "manual work"],
            "lead_gen": ["lead generation", "leads", "prospecting", "cold outreach"],
            "conversion": ["conversion", "closing", "sales cycle"],
            "retention": ["churn", "retention", "customer success"]
        }
        for pain, keywords in pain_keywords.items():
            if any(kw in content_lower for kw in keywords):
                signals["pain_points"].append(pain)

        return signals

    def _extract_objection_args(self, content: str) -> List[str]:
        import re
        objections = []

        objection_patterns = [
            r"(?i)objection[s]?[:\-]\s*(.+)",
            r"(?i)common objection[s]?[:\-]\s*(.+)",
            r"(?i)why (not|don't) .* buy[:\-]\s*(.+)",
            r"(?i)competitor[s]?[:\-]\s*(.+)",
            r"(?i)alternative[s]?[:\-]\s*(.+)",
        ]

        for pattern in objection_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    objections.extend([m.strip() for m in match if m.strip()])
                else:
                    objections.append(match.strip())

        return list(set(objections))[:10]

    def _extract_pricing_signals(self, content: str) -> Dict[str, Any]:
        import re
        signals = {
            "setup_fee": None,
            "monthly_range": None,
            "commission_model": None,
            "pricing_tiers": []
        }

        setup_match = re.search(r"(?i)(?:setup|implementation|onboard).{0,20}?\$?(\d{3,5})", content)
        if setup_match:
            signals["setup_fee"] = int(setup_match.group(1))

        monthly_matches = re.findall(r"(?i)(?:monthly|/month|per month).{0,10}?\$?(\d{2,4})", content)
        if monthly_matches:
            prices = [int(m) for m in monthly_matches]
            signals["monthly_range"] = [min(prices), max(prices)]

        if re.search(r"(?i)zero commission|no commission|commission-free", content):
            signals["commission_model"] = "zero"
        elif re.search(r"(?i)\d+% commission|commission.*\d+%", content):
            signals["commission_model"] = "percentage"

        return signals

    def _extract_tech_stack(self, content: str, files: Dict[str, str]) -> List[str]:
        stack = []
        content_lower = content.lower()

        tech_keywords = {
            "react": ["react", "nextjs", "next.js"],
            "vue": ["vue", "nuxt"],
            "python": ["python", "django", "fastapi", "flask"],
            "node": ["node.js", "nodejs", "express", "nest"],
            "postgresql": ["postgresql", "postgres", "supabase"],
            "redis": ["redis"],
            "aws": ["aws", "amazon web services"],
            "gcp": ["gcp", "google cloud"],
            "docker": ["docker", "kubernetes", "k8s"],
            "typescript": ["typescript", "tsconfig"],
            "tailwind": ["tailwind"],
        }

        for tech, keywords in tech_keywords.items():
            if any(kw in content_lower for kw in keywords):
                stack.append(tech)

        if "package.json" in files:
            try:
                pkg = json.loads(files["package.json"])
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                for dep in deps:
                    if dep not in stack:
                        stack.append(dep)
            except Exception:
                pass

        return stack[:20]

    def _extract_target_market(self, content: str) -> str:
        import re
        patterns = [
            r"(?i)target (?:market|audience|customer)[:\-]\s*(.+)",
            r"(?i)ideal customer[:\-]\s*(.+)",
            r"(?i)we (?:help|serve|target) (.+)",
            r"(?i)built for (.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()[:200]

        return ""

    async def close(self):
        await self.client.aclose()


class ICPDeductionService:
    def __init__(self):
        self.github_service = GitHubIngestionService()
        self.settings = get_settings()

    async def deduce_icp_and_rules(self, campaign_id: UUID, repo_url: str) -> Dict[str, Any]:
        analysis = await self.github_service.analyze_repository(repo_url)
        ai_rules = self._generate_ai_rules(analysis)

        # Save analysis to database
        try:
            await execute("""
                INSERT INTO github_analyses (campaign_id, repo_url, repo_owner, repo_name, analysis, suggested_ai_rules)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (campaign_id) DO UPDATE SET
                    analysis = EXCLUDED.analysis,
                    suggested_ai_rules = EXCLUDED.suggested_ai_rules,
                    updated_at = NOW()
            """, campaign_id, repo_url, analysis.get("repository", "").split("/")[0], analysis.get("repository", "").split("/")[1],
                json.dumps(analysis), json.dumps(ai_rules.model_dump() if ai_rules else None))
        except Exception as e:
            print(f"Error saving GitHub analysis: {e}")

        return {
            "campaign_id": str(campaign_id),
            "analysis": analysis,
            "suggested_ai_rules": ai_rules.model_dump() if ai_rules else None
        }

    def _generate_ai_rules(self, analysis: Dict[str, Any]) -> Optional[AIRules]:
        pricing = analysis.get("pricing_signals", {})
        icp = analysis.get("icp_profile", {})

        return AIRules(
            min_setup_price=pricing.get("setup_fee") or 1200,
            monthly_fee_range=tuple(pricing.get("monthly_range") or [25, 50]),
            zero_commission_rule=pricing.get("commission_model") == "zero"
        )