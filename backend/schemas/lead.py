from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    NOVO = "NOVO"
    APRESENTADO = "APRESENTADO"
    NEGOCIACAO = "NEGOCIACAO"
    FECHADO = "FECHADO"
    REJEITADO = "REJEITADO"


class LeadCreate(BaseModel):
    campaign_id: UUID
    business_name: str = Field(min_length=2, description="Nome do negócio inválido")
    phone_number: str = Field(pattern=r"^\+?[1-9]\d{1,14}$", description="Padrão internacional exigido (E.164)")
    preview_url: Optional[HttpUrl] = None


class LeadUpdate(BaseModel):
    business_name: Optional[str] = Field(default=None, min_length=2)
    phone_number: Optional[str] = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    preview_url: Optional[HttpUrl] = None
    status: Optional[LeadStatus] = None
    calls_count: Optional[int] = Field(default=None, ge=0, le=1, description="Bloqueio: Limite estrito de 1 ligação excedido")


class LeadResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    business_name: str
    phone_number: str
    preview_url: Optional[str]
    calls_count: int
    status: LeadStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadKanbanMove(BaseModel):
    lead_id: UUID
    new_status: LeadStatus