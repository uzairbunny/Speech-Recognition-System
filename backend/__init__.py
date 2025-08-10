"""
Real-Time Speech Recognition & Speaker Identification System Backend

This package contains the core backend functionality for the speech recognition system,
including speech processing, WebSocket handling, database operations, and export services.
"""

__version__ = "1.0.0"
__author__ = "Speech Recognition System"
__description__ = "Real-Time Speech Recognition & Speaker Identification System Backend"

from .config import settings
from .speech_processor import SpeechProcessor
from .websocket_manager import manager
from .database import TranscriptRepository, SpeakerRepository
from .export_service import exporter

__all__ = [
    "settings",
    "SpeechProcessor", 
    "manager",
    "TranscriptRepository",
    "SpeakerRepository", 
    "exporter"
]
