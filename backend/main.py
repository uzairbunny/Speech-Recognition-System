from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
import json
import uuid
from typing import List, Optional
from datetime import datetime
import os

from .config import settings
from .database import connect_to_mongo, close_mongo_connection, TranscriptRepository, SpeakerRepository
from .websocket_manager import manager
from .export_service import exporter
from .models import TranscriptSession, SpeakerProfile, SpeakerSegment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Real-Time Speech Recognition & Speaker Identification System",
    description="A system that transcribes live conversations and identifies speakers in real time",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for frontend)
if os.path.exists("../frontend/build"):
    app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")

# Initialize repositories
transcript_repo = TranscriptRepository()
speaker_repo = SpeakerRepository()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Real-Time Speech Recognition System...")
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Initialize WebSocket manager and speech processor
    await manager.initialize()
    
    # Create exports directory
    os.makedirs("exports", exist_ok=True)
    
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down application...")
    await close_mongo_connection()
    logger.info("Application shutdown complete")


# WebSocket endpoint for real-time transcription
@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """WebSocket endpoint for real-time speech processing"""
    await manager.connect(websocket, connection_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle the message
            await manager.handle_message(websocket, connection_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
        logger.info(f"Client {connection_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        manager.disconnect(connection_id)


# REST API Endpoints

@app.get("/")
async def root():
    """Serve the frontend application"""
    if os.path.exists("../frontend/build/index.html"):
        return FileResponse("../frontend/build/index.html")
    return {"message": "Real-Time Speech Recognition System API", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/api/sessions")
async def get_sessions(limit: int = 100):
    """Get all transcription sessions"""
    try:
        sessions = await transcript_repo.get_all_sessions(limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific transcription session"""
    try:
        session = await transcript_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch session")


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a transcription session"""
    try:
        session = await transcript_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        await transcript_repo.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")


@app.post("/api/sessions/{session_id}/export")
async def export_session(session_id: str, format_type: str = "txt"):
    """Export a transcription session"""
    try:
        # Get session data
        session = await transcript_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get speaker names
        speakers = await speaker_repo.get_all_speakers()
        speaker_names = {speaker["_id"]: speaker["name"] for speaker in speakers}
        
        # Export transcript
        file_path = exporter.export_transcript(session, format_type, speaker_names)
        
        return {
            "message": "Export completed successfully",
            "file_path": file_path,
            "download_url": f"/api/download/{os.path.basename(file_path)}"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to export session")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download exported transcript file"""
    try:
        file_path = os.path.join("exports", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            file_path, 
            filename=filename,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@app.get("/api/speakers")
async def get_speakers():
    """Get all speaker profiles"""
    try:
        speakers = await speaker_repo.get_all_speakers()
        return {"speakers": speakers}
    except Exception as e:
        logger.error(f"Error fetching speakers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch speakers")


@app.post("/api/speakers")
async def create_speaker(
    name: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Create a new speaker profile from audio file"""
    try:
        # Read audio file
        audio_content = await audio_file.read()
        
        # Process audio to extract embedding
        audio_array = manager.speech_processor.preprocess_audio(audio_content)
        embedding = await manager.speech_processor.get_speaker_embedding(
            audio_array, 0, len(audio_array) / settings.sample_rate
        )
        
        if embedding is None:
            raise HTTPException(status_code=400, detail="Failed to extract speaker embedding from audio")
        
        # Create speaker profile
        speaker_data = {
            "name": name,
            "voice_embedding": embedding.tolist(),
            "created_at": datetime.utcnow(),
            "sample_count": 1,
            "metadata": {"uploaded_filename": audio_file.filename}
        }
        
        speaker_id = await speaker_repo.create_speaker(speaker_data)
        
        # Add to speech processor
        manager.speech_processor.add_known_speaker(name, embedding)
        
        return {
            "message": "Speaker created successfully",
            "speaker_id": speaker_id,
            "name": name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating speaker: {e}")
        raise HTTPException(status_code=500, detail="Failed to create speaker")


@app.get("/api/speakers/{speaker_id}")
async def get_speaker(speaker_id: str):
    """Get a specific speaker profile"""
    try:
        speaker = await speaker_repo.get_speaker(speaker_id)
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        return speaker
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching speaker {speaker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch speaker")


@app.delete("/api/speakers/{speaker_id}")
async def delete_speaker(speaker_id: str):
    """Delete a speaker profile"""
    try:
        speaker = await speaker_repo.get_speaker(speaker_id)
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        # Remove from speech processor
        if speaker["name"] in manager.speech_processor.known_speakers:
            del manager.speech_processor.known_speakers[speaker["name"]]
        
        await speaker_repo.delete_speaker(speaker_id)
        return {"message": "Speaker deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting speaker {speaker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete speaker")


@app.post("/api/upload-audio")
async def upload_audio_file(
    session_id: str = Form(...),
    audio_file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """Upload and process audio file for batch transcription"""
    try:
        # Verify session exists
        session = await transcript_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Read audio file
        audio_content = await audio_file.read()
        
        # Process audio
        segments = await manager.speech_processor.process_audio_chunk(
            audio_content, 
            settings.sample_rate,
            language
        )
        
        # Store segments in database
        for segment in segments:
            segment_dict = {
                "speaker_id": segment.speaker_id,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text,
                "confidence": segment.confidence,
                "timestamp": datetime.utcnow()
            }
            
            await transcript_repo.add_segment(session_id, segment_dict)
        
        # Update session
        await transcript_repo.update_session(session_id, {
            "audio_file_path": audio_file.filename,
            "updated_at": datetime.utcnow()
        })
        
        return {
            "message": "Audio file processed successfully",
            "segments_added": len(segments),
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio file: {e}")
        raise HTTPException(status_code=500, detail="Failed to process audio file")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )
