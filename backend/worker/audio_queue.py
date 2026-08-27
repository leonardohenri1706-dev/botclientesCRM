import asyncio
import uuid
import random
import httpx
import base64
import os
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from schemas.audio import AudioGenerationRequest, AudioGenerationResponse, VoiceProcessingJob, IAResponse, LeadContext
from schemas.lead import LeadStatus
from config.settings import get_settings
from config.database import execute, fetchrow, fetch


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueuedJob:
    job_id: str
    lead_id: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3


class AudioQueue:
    def __init__(self, max_concurrent: int = 1):
        self.settings = get_settings()
        self.max_concurrent = max_concurrent
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing: Dict[str, QueuedJob] = {}
        self.completed: Dict[str, QueuedJob] = {}
        self.worker_task: Optional[asyncio.Task] = None
        self.client = httpx.AsyncClient(timeout=300.0)
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        print(f"Audio queue started with max_concurrent={self.max_concurrent}")

    async def stop(self):
        self._running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        await self.client.aclose()
        print("Audio queue stopped")

    async def enqueue(self, lead_id: str, payload: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        job = QueuedJob(job_id=job_id, lead_id=lead_id, payload=payload)
        await self.queue.put(job)
        
        # Save to database
        try:
            await execute("""
                INSERT INTO audio_jobs (id, lead_id, campaign_id, text, voice_id, output_format, status)
                VALUES ($1, $2, (SELECT campaign_id FROM leads WHERE id = $2), $3, $4, $5, 'pending')
            """, job_id, lead_id, payload.get("text", ""), payload.get("voice_id", "default"), payload.get("output_format", "ogg"))
        except Exception as e:
            print(f"Error saving audio job to DB: {e}")
        
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[QueuedJob]:
        if job_id in self.processing:
            return self.processing[job_id]
        if job_id in self.completed:
            return self.completed[job_id]
        
        # Try to load from database
        try:
            row = await fetchrow("SELECT * FROM audio_jobs WHERE id = $1", job_id)
            if row:
                job = QueuedJob(
                    job_id=row["id"],
                    lead_id=row["lead_id"],
                    payload={"text": row["text"], "voice_id": row["voice_id"], "output_format": row["output_format"]},
                    status=JobStatus(row["status"]),
                    result={"file_path": row["file_path"], "duration_seconds": row["duration_seconds"], "file_size_bytes": row["file_size_bytes"]} if row["file_path"] else None,
                    error=row["error_message"],
                    created_at=row["created_at"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    retries=row["retries"]
                )
                return job
        except Exception as e:
            print(f"Error loading job from DB: {e}")
        
        return None

    async def _worker_loop(self):
        while self._running:
            try:
                while len(self.processing) >= self.max_concurrent:
                    await asyncio.sleep(1)
                    if not self._running:
                        return

                try:
                    job = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                asyncio.create_task(self._process_job(job))

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker loop error: {e}")
                await asyncio.sleep(5)

    async def _process_job(self, job: QueuedJob):
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        self.processing[job.job_id] = job

        # Update DB
        try:
            await execute("UPDATE audio_jobs SET status = 'processing', started_at = NOW() WHERE id = $1", job.job_id)
        except Exception as e:
            print(f"Error updating job status: {e}")

        try:
            result = await self._execute_audio_generation(job)
            job.result = result
            job.status = JobStatus.COMPLETED
            
            # Update lead and audio_jobs
            try:
                await execute("""
                    UPDATE leads SET status = 'APRESENTADO', calls_count = 1, audio_path = $1, audio_generated_at = NOW()
                    WHERE id = $2
                """, result.get("file_path"), job.lead_id)
                
                await execute("""
                    UPDATE audio_jobs SET status = 'completed', file_path = $1, duration_seconds = $2, file_size_bytes = $3, completed_at = NOW()
                    WHERE id = $4
                """, result.get("file_path"), result.get("duration_seconds", 0), result.get("file_size_bytes", 0), job.job_id)
            except Exception as e:
                print(f"Error updating lead/audio_job: {e}")
                
        except Exception as e:
            job.error = str(e)
            job.retries += 1

            if job.retries < job.max_retries:
                job.status = JobStatus.PENDING
                await asyncio.sleep(2 ** job.retries)
                await self.queue.put(job)
                del self.processing[job.job_id]
                return
            else:
                job.status = JobStatus.FAILED
                try:
                    await execute("UPDATE audio_jobs SET status = 'failed', error_message = $1 WHERE id = $2", str(e), job.job_id)
                except Exception as db_e:
                    print(f"Error updating failed job: {db_e}")

        job.completed_at = datetime.utcnow()
        self.completed[job.job_id] = job
        del self.processing[job.job_id]

        if len(self.completed) > 1000:
            oldest = min(self.completed.keys(), key=lambda k: self.completed[k].completed_at)
            del self.completed[oldest]

    async def _execute_audio_generation(self, job: QueuedJob) -> Dict[str, Any]:
        payload = job.payload
        lead_id = job.lead_id
        text = payload.get("text", "")
        voice_id = payload.get("voice_id", "default")
        output_format = payload.get("output_format", "ogg")

        voice_url = f"{self.settings.VOICE_API_URL}/generate-audio"
        headers = {}
        if self.settings.VOICE_API_KEY:
            headers["Authorization"] = f"Bearer {self.settings.VOICE_API_KEY}"

        response = await self.client.post(
            voice_url,
            json={
                "text": text,
                "output_filename": f"lead_{lead_id}",
                "voice_id": voice_id,
                "format": output_format
            },
            headers=headers
        )
        response.raise_for_status()
        voice_data = response.json()

        return {
            "file_path": voice_data.get("file"),
            "duration_seconds": voice_data.get("duration", 0),
            "file_size_bytes": voice_data.get("size", 0)
        }


class EvolutionAPIClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = self.settings.EVOLUTION_API_KEY
        self.instance = self.settings.EVOLUTION_INSTANCE_NAME
        self.client = httpx.AsyncClient(timeout=60.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def send_presence(
        self,
        phone_number: str,
        presence: str,
        delay_ms: int
    ) -> bool:
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {
            "number": phone_number,
            "presence": presence,
            "delay": delay_ms
        }

        response = await self.client.post(url, json=payload, headers=self._headers())
        return response.status_code == 200 or response.status_code == 201

    async def send_text_message(
        self,
        phone_number: str,
        text: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": phone_number,
            "text": text
        }

        response = await self.client.post(url, json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    async def send_audio_message(
        self,
        phone_number: str,
        audio_path: str,
        ptt: bool = True
    ) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with open(audio_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")

        url = f"{self.base_url}/message/sendWhatsAppAudio/{self.instance}"
        payload = {
            "number": phone_number,
            "audio": audio_base64,
            "ptt": ptt
        }

        response = await self.client.post(url, json=payload, headers=self._headers())
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


class HumanBehaviorSimulator:
    def __init__(self):
        self.settings = get_settings()

    def random_delay(self, min_ms: int, max_ms: int) -> int:
        return random.randint(min_ms, max_ms)

    async def simulate_typing(self, evolution: EvolutionAPIClient, phone_number: str) -> None:
        delay = self.random_delay(
            self.settings.TYPING_DELAY_MIN,
            self.settings.TYPING_DELAY_MAX
        )
        await evolution.send_presence(phone_number, "composing", delay)
        await asyncio.sleep(delay / 1000)

    async def simulate_recording(self, evolution: EvolutionAPIClient, phone_number: str) -> None:
        delay = self.random_delay(
            self.settings.RECORDING_DELAY_MIN,
            self.settings.RECORDING_DELAY_MAX
        )
        await evolution.send_presence(phone_number, "recording", delay)
        await asyncio.sleep(delay / 1000)

    async def anti_ban_delay(self) -> None:
        delay = self.random_delay(
            self.settings.MIN_DELAY_BETWEEN_CALLS * 1000,
            self.settings.MAX_DELAY_BETWEEN_CALLS * 1000
        )
        await asyncio.sleep(delay / 1000)


class OutreachOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.audio_queue = AudioQueue(max_concurrent=self.settings.MAX_CONCURRENT_AUDIO_JOBS)
        self.evolution = EvolutionAPIClient()
        self.simulator = HumanBehaviorSimulator()

    async def start(self):
        await self.audio_queue.start()

    async def stop(self):
        await self.audio_queue.stop()
        await self.evolution.close()

    async def process_lead(
        self,
        lead_id: str,
        phone_number: str,
        ia_response: IAResponse,
        lead_context: LeadContext
    ) -> Dict[str, Any]:
        audio_path = None

        if ia_response.needs_audio and ia_response.audio_text:
            job_id = await self.audio_queue.enqueue(lead_id, {
                "text": ia_response.audio_text,
                "voice_id": "default",
                "output_format": "ogg"
            })
            
            for _ in range(self.settings.AUDIO_QUEUE_TIMEOUT):
                job = await self.audio_queue.get_job_status(job_id)
                if job and job.status == JobStatus.COMPLETED:
                    audio_path = job.result.get("file_path")
                    break
                elif job and job.status == JobStatus.FAILED:
                    raise Exception(f"Audio generation failed: {job.error}")
                await asyncio.sleep(1)
            else:
                raise TimeoutError("Audio generation timed out")

        await self.simulator.simulate_typing(self.evolution, phone_number)
        await self.evolution.send_text_message(phone_number, ia_response.text_message)

        if audio_path:
            await self.simulator.simulate_recording(self.evolution, phone_number)
            await self.evolution.send_audio_message(phone_number, audio_path, ptt=True)

        try:
            await execute("""
                UPDATE leads SET status = 'APRESENTADO', calls_count = 1, last_contact_at = NOW()
                WHERE id = $1
            """, lead_id)
            
            await execute("""
                INSERT INTO outreach_logs (lead_id, campaign_id, phone_number, text_message, audio_sent, audio_path, ia_intent, status)
                VALUES ($1, (SELECT campaign_id FROM leads WHERE id = $1), $2, $3, $4, $5, $6, 'sent')
            """, lead_id, phone_number, ia_response.text_message, audio_path is not None, audio_path, ia_response.intent)
        except Exception as e:
            print(f"Error logging outreach: {e}")

        await self.simulator.anti_ban_delay()

        return {
            "lead_id": lead_id,
            "status": "sent",
            "audio_sent": audio_path is not None,
            "timestamp": datetime.utcnow().isoformat()
        }


_audio_queue: Optional[AudioQueue] = None
_outreach_orchestrator: Optional[OutreachOrchestrator] = None


async def get_audio_queue() -> AudioQueue:
    global _audio_queue
    if _audio_queue is None:
        _audio_queue = AudioQueue()
        await _audio_queue.start()
    return _audio_queue


async def get_outreach_orchestrator() -> OutreachOrchestrator:
    global _outreach_orchestrator
    if _outreach_orchestrator is None:
        _outreach_orchestrator = OutreachOrchestrator()
        await _outreach_orchestrator.start()
    return _outreach_orchestrator


async def shutdown_services():
    global _audio_queue, _outreach_orchestrator
    if _audio_queue:
        await _audio_queue.stop()
        _audio_queue = None
    if _outreach_orchestrator:
        await _outreach_orchestrator.stop()
        _outreach_orchestrator = None