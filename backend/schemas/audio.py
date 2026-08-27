from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID


class AudioGenerationRequest(BaseModel):
    lead_id: UUID
    text: str = Field(min_length=1, max_length=5000)
    voice_id: str = Field(default="default")
    output_format: Literal["ogg", "mp3", "wav"] = Field(default="ogg")


class AudioGenerationResponse(BaseModel):
    file_path: str
    duration_seconds: float
    file_size_bytes: int


class VoiceProcessingJob(BaseModel):
    job_id: UUID
    lead_id: UUID
    text: str
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    audio_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class IAResponse(BaseModel):
    text_message: str
    needs_audio: bool
    audio_text: Optional[str] = None
    intent: Literal["presentation", "objection_handling", "closing", "followup"]


class LeadContext(BaseModel):
    business_name: str
    preview_url: Optional[str] = None
    niche: Optional[str] = None
    ai_rules: Optional[dict] = None