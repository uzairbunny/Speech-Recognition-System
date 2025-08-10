from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class SpeakerSegment(BaseModel):
    speaker_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float = 0.0


class TranscriptSession(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    session_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    segments: List[SpeakerSegment] = []
    speakers: Dict[str, Dict[str, Any]] = {}  # speaker_id -> metadata
    audio_file_path: Optional[str] = None
    language: Optional[str] = None
    status: str = "active"  # active, completed, paused
    total_duration: float = 0.0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class SpeakerProfile(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    voice_embedding: List[float] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sample_count: int = 0
    metadata: Dict[str, Any] = {}

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TranscriptExport(BaseModel):
    session_id: str
    export_format: str  # "txt", "srt", "json"
    file_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AudioChunk(BaseModel):
    timestamp: float
    audio_data: bytes
    sample_rate: int
    channels: int
