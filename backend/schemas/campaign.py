from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from uuid import UUID


class AIRules(BaseModel):
    min_setup_price: float = Field(default=1200, ge=0)
    monthly_fee_range: tuple[float, float] = Field(default=(25, 50))
    zero_commission_rule: bool = Field(default=True)


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, description="O nome da campanha é obrigatório")
    github_repo_url: HttpUrl = Field(description="Deve ser uma URL válida do GitHub")
    target_niche: Optional[str] = None
    ai_rules: Optional[AIRules] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3)
    github_repo_url: Optional[HttpUrl] = None
    target_niche: Optional[str] = None
    ai_rules: Optional[AIRules] = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    github_repo_url: str
    target_niche: Optional[str]
    ai_rules: Optional[AIRules]
    user_id: UUID
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True