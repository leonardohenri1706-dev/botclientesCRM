from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID
import uvicorn

from config.settings import get_settings
from config.database import get_pool, close_pool, execute, fetch, fetchrow, fetchval
from schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadStatus, LeadKanbanMove
from schemas.scraping import ScrapingRequest, ScrapingResponse
from schemas.audio import IAResponse, LeadContext
from app.services.scraping_service import ScrapingService
from app.services.github_ingestion import ICPDeductionService
from worker.audio_queue import get_outreach_orchestrator, shutdown_services, get_audio_queue


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting BotClientes Backend...")
    orchestrator = await get_outreach_orchestrator()
    yield
    print("Shutting down...")
    await shutdown_services()
    await close_pool()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "botclientes-backend"}


@app.post(f"{settings.API_V1_PREFIX}/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign: CampaignCreate):
    user_id = "00000000-0000-0000-0000-000000000000"
    
    row = await fetchrow("""
        INSERT INTO campaigns (user_id, name, github_repo_url, target_niche, ai_rules)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """, user_id, campaign.name, str(campaign.github_repo_url), campaign.target_niche, 
        campaign.ai_rules.model_dump_json() if campaign.ai_rules else None)
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create campaign")
    
    return dict(row)


@app.get(f"{settings.API_V1_PREFIX}/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(skip: int = 0, limit: int = 50):
    rows = await fetch("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT $1 OFFSET $2", limit, skip)
    return [dict(row) for row in rows]


@app.get(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID):
    row = await fetchrow("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return dict(row)


@app.patch(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}", response_model=CampaignResponse)
async def update_campaign(campaign_id: UUID, campaign: CampaignUpdate):
    update_data = campaign.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Build dynamic query
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    row = await fetchrow(f"""
        UPDATE campaigns SET {set_clause}, updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """, campaign_id, *values)
    
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return dict(row)


@app.delete(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(campaign_id: UUID):
    result = await execute("DELETE FROM campaigns WHERE id = $1", campaign_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Campaign not found")


@app.post(f"{settings.API_V1_PREFIX}/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(lead: LeadCreate):
    row = await fetchrow("""
        INSERT INTO leads (campaign_id, business_name, phone_number, preview_url, status, calls_count)
        VALUES ($1, $2, $3, $4, 'NOVO', 0)
        RETURNING *
    """, lead.campaign_id, lead.business_name, lead.phone_number, lead.preview_url)
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create lead")
    return dict(row)


@app.get(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}/leads", response_model=List[LeadResponse])
async def list_leads(campaign_id: UUID, status: Optional[LeadStatus] = None, skip: int = 0, limit: int = 100):
    if status:
        rows = await fetch("""
            SELECT * FROM leads WHERE campaign_id = $1 AND status = $2
            ORDER BY created_at DESC LIMIT $3 OFFSET $4
        """, campaign_id, status.value, limit, skip)
    else:
        rows = await fetch("""
            SELECT * FROM leads WHERE campaign_id = $1
            ORDER BY created_at DESC LIMIT $2 OFFSET $3
        """, campaign_id, limit, skip)
    return [dict(row) for row in rows]


@app.get(f"{settings.API_V1_PREFIX}/leads/{{lead_id}}", response_model=LeadResponse)
async def get_lead(lead_id: UUID):
    row = await fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return dict(row)


@app.patch(f"{settings.API_V1_PREFIX}/leads/{{lead_id}}", response_model=LeadResponse)
async def update_lead(lead_id: UUID, lead: LeadUpdate):
    update_data = lead.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    row = await fetchrow(f"""
        UPDATE leads SET {set_clause}, updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """, lead_id, *values)
    
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(row)


@app.post(f"{settings.API_V1_PREFIX}/leads/{{lead_id}}/move", response_model=LeadResponse)
async def move_lead_in_kanban(lead_id: UUID, move: LeadKanbanMove):
    existing = await fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = {"status": move.new_status.value}
    if move.new_status == LeadStatus.APRESENTADO and existing["calls_count"] == 0:
        update_data["calls_count"] = 1
    
    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())])
    values = list(update_data.values())
    
    row = await fetchrow(f"""
        UPDATE leads SET {set_clause}, updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """, lead_id, *values)
    
    if not row:
        raise HTTPException(status_code=500, detail="Failed to move lead")
    
    return dict(row)


@app.post(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}/scrape", response_model=ScrapingResponse)
async def scrape_campaign(campaign_id: UUID, request: ScrapingRequest):
    campaign = await fetchrow("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    request.campaign_id = campaign_id
    
    scraping_service = ScrapingService()
    try:
        response = await scraping_service.execute_scraping(request)
        await scraping_service.close()
        return response
    except Exception as e:
        await scraping_service.close()
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@app.post(f"{settings.API_V1_PREFIX}/campaigns/{{campaign_id}}/analyze-repo")
async def analyze_github_repo(campaign_id: UUID):
    campaign = await fetchrow("SELECT * FROM campaigns WHERE id = $1", campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    repo_url = campaign["github_repo_url"]
    if not repo_url:
        raise HTTPException(status_code=400, detail="Campaign has no GitHub repository URL")
    
    icp_service = ICPDeductionService()
    try:
        result = await icp_service.deduce_icp_and_rules(campaign_id, repo_url)
        await icp_service.github_service.close()
        return result
    except Exception as e:
        await icp_service.github_service.close()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post(f"{settings.API_V1_PREFIX}/leads/{{lead_id}}/outreach")
async def trigger_outreach(lead_id: UUID, ia_response: IAResponse, lead_context: LeadContext):
    lead = await fetchrow("SELECT * FROM leads WHERE id = $1", lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    phone_number = lead["phone_number"]
    if not phone_number:
        raise HTTPException(status_code=400, detail="Lead has no phone number")
    
    orchestrator = await get_outreach_orchestrator()
    
    try:
        result = await orchestrator.process_lead(
            lead_id=str(lead_id),
            phone_number=phone_number,
            ia_response=ia_response,
            lead_context=lead_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outreach failed: {str(e)}")


@app.get(f"{settings.API_V1_PREFIX}/audio/queue/status")
async def get_queue_status():
    queue = await get_audio_queue()
    return {
        "queue_size": queue.queue.qsize(),
        "processing": len(queue.processing),
        "completed": len(queue.completed),
        "max_concurrent": queue.max_concurrent
    }


@app.get(f"{settings.API_V1_PREFIX}/audio/jobs/{{job_id}}")
async def get_audio_job_status(job_id: str):
    queue = await get_audio_queue()
    job = await queue.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "lead_id": job.lead_id,
        "status": job.status.value,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "retries": job.retries
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)