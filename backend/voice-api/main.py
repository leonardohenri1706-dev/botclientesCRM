from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Literal
import uvicorn
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
import subprocess
import json

app = FastAPI(title="Voice API - RTX 3050 Local TTS", version="1.0.0")

# Configuration
OUTPUT_DIR = Path("/app/audio_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Model options: "tts_models/multilingual/multi-dataset/xtts_v2" (Coqui XTTS v2)
# Or use edge-tts for lighter weight
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge-tts")  # "edge-tts", "coqui", "piper"
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "pt-BR-ThalitaNeural")

class AudioGenerationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    output_filename: str = Field(default="output")
    voice_id: str = Field(default=DEFAULT_VOICE)
    format: Literal["ogg", "mp3", "wav"] = Field(default="ogg")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)

class AudioGenerationResponse(BaseModel):
    file: str
    duration_seconds: float
    size: int
    format: str

class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    result: Optional[AudioGenerationResponse] = None
    error: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

# In-memory job store (use Redis in production)
jobs: dict[str, JobStatus] = {}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "voice-api",
        "tts_engine": TTS_ENGINE,
        "default_voice": DEFAULT_VOICE
    }


@app.post("/generate-audio", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest, background_tasks: BackgroundTasks):
    """Generate audio file from text using local TTS"""
    job_id = str(uuid.uuid4())
    
    job = JobStatus(
        job_id=job_id,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )
    jobs[job_id] = job
    
    # Process in background
    background_tasks.add_task(process_audio_generation, job_id, request)
    
    # For synchronous response, wait for completion (with timeout)
    # In production, return job_id immediately and poll /jobs/{job_id}
    for _ in range(300):  # 5 min timeout
        await asyncio.sleep(1)
        job = jobs.get(job_id)
        if job and job.status == "completed":
            return job.result
        elif job and job.status == "failed":
            raise HTTPException(status_code=500, detail=job.error)
    
    raise HTTPException(status_code=504, detail="Audio generation timed out")


@app.post("/generate-audio-async", response_model=JobStatus)
async def generate_audio_async(request: AudioGenerationRequest, background_tasks: BackgroundTasks):
    """Generate audio asynchronously - returns job_id immediately"""
    job_id = str(uuid.uuid4())
    
    job = JobStatus(
        job_id=job_id,
        status="pending",
        created_at=datetime.utcnow().isoformat()
    )
    jobs[job_id] = job
    
    background_tasks.add_task(process_audio_generation, job_id, request)
    
    return job


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def process_audio_generation(job_id: str, request: AudioGenerationRequest):
    job = jobs[job_id]
    job.status = "processing"
    job.started_at = datetime.utcnow().isoformat()
    
    try:
        output_path = OUTPUT_DIR / f"{request.output_filename}.{request.format}"
        
        if TTS_ENGINE == "edge-tts":
            result = await generate_with_edge_tts(request, output_path)
        elif TTS_ENGINE == "coqui":
            result = await generate_with_coqui(request, output_path)
        elif TTS_ENGINE == "piper":
            result = await generate_with_piper(request, output_path)
        else:
            raise ValueError(f"Unknown TTS engine: {TTS_ENGINE}")
        
        job.result = AudioGenerationResponse(**result)
        job.status = "completed"
        job.completed_at = datetime.utcnow().isoformat()
        
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.completed_at = datetime.utcnow().isoformat()
        print(f"Audio generation failed: {e}")


async def generate_with_edge_tts(request: AudioGenerationRequest, output_path: Path) -> dict:
    """Generate audio using Microsoft Edge TTS (free, high quality, no GPU needed)"""
    import edge_tts
    
    communicate = edge_tts.Communicate(
        text=request.text,
        voice=request.voice_id,
        rate=f"{int((request.speed - 1) * 100)}%" if request.speed != 1.0 else "+0%"
    )
    
    # Save as temporary mp3 first
    temp_mp3 = output_path.with_suffix(".mp3")
    await communicate.save(str(temp_mp3))
    
    # Convert to requested format if needed
    if request.format != "mp3":
        await convert_audio(temp_mp3, output_path, request.format)
        temp_mp3.unlink(missing_ok=True)
    else:
        output_path = temp_mp3
    
    # Get duration
    duration = await get_audio_duration(output_path)
    size = output_path.stat().st_size
    
    return {
        "file": str(output_path),
        "duration_seconds": duration,
        "size": size,
        "format": request.format
    }


gpu_lock = asyncio.Lock()
_cached_coqui_tts = None

def get_coqui_tts():
    global _cached_coqui_tts
    if _cached_coqui_tts is None:
        from TTS.api import TTS
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _cached_coqui_tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return _cached_coqui_tts


async def generate_with_coqui(request: AudioGenerationRequest, output_path: Path) -> dict:
    """Generate audio using Coqui XTTS v2 with GPU Lock, FP16 & VRAM cleanup for RTX 3050"""
    import torch
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async with gpu_lock:
        temp_wav = output_path.with_suffix(".wav")
        try:
            tts = get_coqui_tts()
            
            # Síntese neural para WAV
            tts.tts_to_file(
                text=request.text,
                speaker_wav=request.voice_id if request.voice_id != DEFAULT_VOICE else "minha_voz.wav",
                language="pt",
                file_path=str(temp_wav),
                speed=request.speed
            )
            
            # Conversão para Opus/OGG PTT via ffmpeg
            if request.format != "wav":
                await convert_audio(temp_wav, output_path, request.format)
                temp_wav.unlink(missing_ok=True)
            else:
                temp_wav = output_path
                
            duration = await get_audio_duration(output_path)
            size = output_path.stat().st_size
            
            return {
                "file": str(output_path),
                "duration_seconds": duration,
                "size": size,
                "format": request.format
            }
        finally:
            if device == "cuda":
                torch.cuda.empty_cache()
            # Micro-pausa térmica para dissipação no ASUS TUF
            await asyncio.sleep(5)


async def generate_with_piper(request: AudioGenerationRequest, output_path: Path) -> dict:
    """Generate audio using Piper TTS (fast, lightweight, CPU-friendly)"""
    # Piper expects: echo "text" | piper --model <model> --output_file <file>
    model_path = os.getenv("PIPER_MODEL", "/app/models/pt_BR-faber-medium.onnx")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Piper model not found: {model_path}")
    
    process = await asyncio.create_subprocess_exec(
        "piper",
        "--model", model_path,
        "--output_file", str(output_path),
        "--length_scale", str(1.0 / request.speed),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate(input=request.text.encode())
    
    if process.returncode != 0:
        raise RuntimeError(f"Piper failed: {stderr.decode()}")
    
    duration = await get_audio_duration(output_path)
    size = output_path.stat().st_size
    
    return {
        "file": str(output_path),
        "duration_seconds": duration,
        "size": size,
        "format": request.format
    }


async def convert_audio(input_path: Path, output_path: Path, format: str):
    """Convert audio using ffmpeg"""
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(input_path),
        "-c:a", "libopus" if format == "ogg" else "pcm_s16le" if format == "wav" else "libmp3lame",
        "-b:a", "64k",
        str(output_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError("Audio conversion failed")


async def get_audio_duration(file_path: Path) -> float:
    """Get audio duration using ffprobe"""
    process = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, _ = await process.communicate()
    
    try:
        return float(stdout.decode().strip())
    except ValueError:
        return 0.0


@app.get("/voices")
async def list_voices():
    """List available voices for current TTS engine"""
    if TTS_ENGINE == "edge-tts":
        import edge_tts
        voices = await edge_tts.list_voices()
        pt_voices = [v for v in voices if v["Locale"].startswith("pt-")]
        return {"voices": pt_voices, "engine": "edge-tts"}
    elif TTS_ENGINE == "coqui":
        return {"voices": ["default", "custom_speaker"], "engine": "coqui"}
    elif TTS_ENGINE == "piper":
        models_dir = Path("/app/models")
        models = list(models_dir.glob("*.onnx")) if models_dir.exists() else []
        return {"voices": [m.stem for m in models], "engine": "piper"}
    return {"voices": [], "engine": TTS_ENGINE}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)