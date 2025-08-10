import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from .speech_processor import SpeechProcessor
from .database import TranscriptRepository, SpeakerRepository
from .models import TranscriptSession, SpeakerSegment
from datetime import datetime
import base64
import numpy as np

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time transcription"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}  # session_id -> set of connection_ids
        self.speech_processor = SpeechProcessor()
        self.transcript_repo = TranscriptRepository()
        self.speaker_repo = SpeakerRepository()
    
    async def initialize(self):
        """Initialize the speech processor"""
        await self.speech_processor.initialize()
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connection established: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Remove from session connections
        for session_id, connections in self.session_connections.items():
            connections.discard(connection_id)
        
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_session(self, message: dict, session_id: str):
        """Broadcast a message to all connections in a session"""
        if session_id in self.session_connections:
            for connection_id in self.session_connections[session_id].copy():
                await self.send_personal_message(message, connection_id)
    
    def add_connection_to_session(self, connection_id: str, session_id: str):
        """Add a connection to a transcription session"""
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
    
    def remove_connection_from_session(self, connection_id: str, session_id: str):
        """Remove a connection from a transcription session"""
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
    
    async def handle_message(self, websocket: WebSocket, connection_id: str, message: dict):
        """Handle incoming WebSocket messages"""
        try:
            message_type = message.get("type")
            
            if message_type == "start_session":
                await self.handle_start_session(connection_id, message)
            
            elif message_type == "join_session":
                await self.handle_join_session(connection_id, message)
            
            elif message_type == "audio_data":
                await self.handle_audio_data(connection_id, message)
            
            elif message_type == "stop_session":
                await self.handle_stop_session(connection_id, message)
            
            elif message_type == "add_speaker":
                await self.handle_add_speaker(connection_id, message)
            
            elif message_type == "export_transcript":
                await self.handle_export_transcript(connection_id, message)
            
            else:
                await self.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }, connection_id)
        
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": str(e)
            }, connection_id)
    
    async def handle_start_session(self, connection_id: str, message: dict):
        """Handle starting a new transcription session"""
        try:
            session_name = message.get("session_name", f"Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            language = message.get("language")
            
            # Create new session in database
            session_data = {
                "session_name": session_name,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "segments": [],
                "speakers": {},
                "language": language,
                "status": "active",
                "total_duration": 0.0
            }
            
            session_id = await self.transcript_repo.create_session(session_data)
            
            # Add connection to session
            self.add_connection_to_session(connection_id, session_id)
            
            await self.send_personal_message({
                "type": "session_started",
                "session_id": session_id,
                "session_name": session_name
            }, connection_id)
            
            logger.info(f"Started new transcription session: {session_id}")
        
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": "Failed to start session"
            }, connection_id)
    
    async def handle_join_session(self, connection_id: str, message: dict):
        """Handle joining an existing transcription session"""
        try:
            session_id = message.get("session_id")
            
            if not session_id:
                raise ValueError("Session ID is required")
            
            # Verify session exists
            session = await self.transcript_repo.get_session(session_id)
            if not session:
                raise ValueError("Session not found")
            
            # Add connection to session
            self.add_connection_to_session(connection_id, session_id)
            
            await self.send_personal_message({
                "type": "session_joined",
                "session_id": session_id,
                "session_name": session["session_name"],
                "segments": session.get("segments", [])
            }, connection_id)
            
            logger.info(f"Connection {connection_id} joined session: {session_id}")
        
        except Exception as e:
            logger.error(f"Error joining session: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": str(e)
            }, connection_id)
    
    async def handle_audio_data(self, connection_id: str, message: dict):
        """Handle incoming audio data for transcription"""
        try:
            session_id = message.get("session_id")
            if not session_id:
                raise ValueError("Session ID is required")
            
            # Decode audio data
            audio_base64 = message.get("audio_data")
            if not audio_base64:
                raise ValueError("Audio data is required")
            
            audio_bytes = base64.b64decode(audio_base64)
            sample_rate = message.get("sample_rate", 16000)
            language = message.get("language")
            
            # Process audio
            segments = await self.speech_processor.process_audio_chunk(
                audio_bytes, 
                sample_rate, 
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
                
                await self.transcript_repo.add_segment(session_id, segment_dict)
            
            # Broadcast new segments to all session participants
            if segments:
                await self.broadcast_to_session({
                    "type": "new_segments",
                    "session_id": session_id,
                    "segments": [
                        {
                            "speaker_id": seg.speaker_id,
                            "start_time": seg.start_time,
                            "end_time": seg.end_time,
                            "text": seg.text,
                            "confidence": seg.confidence
                        }
                        for seg in segments
                    ]
                }, session_id)
        
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": "Failed to process audio"
            }, connection_id)
    
    async def handle_stop_session(self, connection_id: str, message: dict):
        """Handle stopping a transcription session"""
        try:
            session_id = message.get("session_id")
            if not session_id:
                raise ValueError("Session ID is required")
            
            # Update session status
            await self.transcript_repo.update_session(session_id, {
                "status": "completed",
                "updated_at": datetime.utcnow()
            })
            
            # Notify all session participants
            await self.broadcast_to_session({
                "type": "session_stopped",
                "session_id": session_id
            }, session_id)
            
            # Remove all connections from session
            if session_id in self.session_connections:
                del self.session_connections[session_id]
            
            logger.info(f"Session stopped: {session_id}")
        
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": "Failed to stop session"
            }, connection_id)
    
    async def handle_add_speaker(self, connection_id: str, message: dict):
        """Handle adding a known speaker profile"""
        try:
            speaker_name = message.get("speaker_name")
            audio_sample_base64 = message.get("audio_sample")
            
            if not speaker_name or not audio_sample_base64:
                raise ValueError("Speaker name and audio sample are required")
            
            # Decode audio sample
            audio_bytes = base64.b64decode(audio_sample_base64)
            sample_rate = message.get("sample_rate", 16000)
            
            # Process audio to get embedding
            audio_array = self.speech_processor.preprocess_audio(audio_bytes, sample_rate)
            embedding = await self.speech_processor.get_speaker_embedding(
                audio_array, 0, len(audio_array) / sample_rate
            )
            
            if embedding is None:
                raise ValueError("Failed to extract speaker embedding")
            
            # Store speaker profile
            speaker_data = {
                "name": speaker_name,
                "voice_embedding": embedding.tolist(),
                "created_at": datetime.utcnow(),
                "sample_count": 1,
                "metadata": {}
            }
            
            speaker_id = await self.speaker_repo.create_speaker(speaker_data)
            
            # Add to speech processor
            self.speech_processor.add_known_speaker(speaker_name, embedding)
            
            await self.send_personal_message({
                "type": "speaker_added",
                "speaker_id": speaker_id,
                "speaker_name": speaker_name
            }, connection_id)
            
            logger.info(f"Added speaker profile: {speaker_name}")
        
        except Exception as e:
            logger.error(f"Error adding speaker: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": str(e)
            }, connection_id)
    
    async def handle_export_transcript(self, connection_id: str, message: dict):
        """Handle transcript export request"""
        try:
            session_id = message.get("session_id")
            export_format = message.get("format", "txt")
            
            if not session_id:
                raise ValueError("Session ID is required")
            
            # Get session data
            session = await self.transcript_repo.get_session(session_id)
            if not session:
                raise ValueError("Session not found")
            
            # Generate export file (placeholder - implement in export module)
            file_path = f"exports/{session_id}.{export_format}"
            
            await self.send_personal_message({
                "type": "export_ready",
                "session_id": session_id,
                "format": export_format,
                "file_path": file_path,
                "download_url": f"/api/download/{session_id}.{export_format}"
            }, connection_id)
        
        except Exception as e:
            logger.error(f"Error exporting transcript: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": str(e)
            }, connection_id)


# Global connection manager instance
manager = ConnectionManager()
