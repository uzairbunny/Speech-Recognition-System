from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings
from .models import TranscriptSession, SpeakerProfile
import logging

logger = logging.getLogger(__name__)


class Database:
    client: Optional[AsyncIOMotorClient] = None
    database = None


db = Database()


async def connect_to_mongo():
    """Create database connection"""
    try:
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        db.database = db.client[settings.database_name]
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info("Connected to MongoDB")
        
        # Create indexes
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")


async def create_indexes():
    """Create database indexes for better performance"""
    try:
        # Transcript sessions indexes
        await db.database.transcript_sessions.create_index("session_name")
        await db.database.transcript_sessions.create_index("created_at")
        await db.database.transcript_sessions.create_index("status")
        
        # Speaker profiles indexes
        await db.database.speaker_profiles.create_index("name")
        await db.database.speaker_profiles.create_index("created_at")
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")


def get_database():
    """Get database instance"""
    return db.database


class TranscriptRepository:
    """Repository for transcript operations"""
    
    def __init__(self):
        self.collection = db.database.transcript_sessions
    
    async def create_session(self, session_data: dict) -> str:
        """Create a new transcript session"""
        result = await self.collection.insert_one(session_data)
        return str(result.inserted_id)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get transcript session by ID"""
        from bson import ObjectId
        return await self.collection.find_one({"_id": ObjectId(session_id)})
    
    async def update_session(self, session_id: str, update_data: dict):
        """Update transcript session"""
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )
    
    async def add_segment(self, session_id: str, segment: dict):
        """Add a new segment to transcript session"""
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"segments": segment}}
        )
    
    async def get_all_sessions(self, limit: int = 100):
        """Get all transcript sessions"""
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def delete_session(self, session_id: str):
        """Delete transcript session"""
        from bson import ObjectId
        await self.collection.delete_one({"_id": ObjectId(session_id)})


class SpeakerRepository:
    """Repository for speaker operations"""
    
    def __init__(self):
        self.collection = db.database.speaker_profiles
    
    async def create_speaker(self, speaker_data: dict) -> str:
        """Create a new speaker profile"""
        result = await self.collection.insert_one(speaker_data)
        return str(result.inserted_id)
    
    async def get_speaker(self, speaker_id: str) -> Optional[dict]:
        """Get speaker profile by ID"""
        from bson import ObjectId
        return await self.collection.find_one({"_id": ObjectId(speaker_id)})
    
    async def get_speaker_by_name(self, name: str) -> Optional[dict]:
        """Get speaker profile by name"""
        return await self.collection.find_one({"name": name})
    
    async def update_speaker(self, speaker_id: str, update_data: dict):
        """Update speaker profile"""
        from bson import ObjectId
        await self.collection.update_one(
            {"_id": ObjectId(speaker_id)},
            {"$set": update_data}
        )
    
    async def get_all_speakers(self):
        """Get all speaker profiles"""
        cursor = self.collection.find()
        return await cursor.to_list(length=None)
    
    async def delete_speaker(self, speaker_id: str):
        """Delete speaker profile"""
        from bson import ObjectId
        await self.collection.delete_one({"_id": ObjectId(speaker_id)})
