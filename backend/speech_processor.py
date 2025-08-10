import whisper
import torch
import torchaudio
import numpy as np
import librosa
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
import logging
from typing import List, Tuple, Dict, Optional
import tempfile
import os
from .config import settings
from .models import SpeakerSegment
import io
import wave

logger = logging.getLogger(__name__)


class SpeechProcessor:
    """Main speech processing class combining Whisper and pyannote"""
    
    def __init__(self):
        self.whisper_model = None
        self.diarization_pipeline = None
        self.embedding_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sample_rate = settings.sample_rate
        self.known_speakers = {}  # speaker_name -> embedding
        
    async def initialize(self):
        """Initialize all models"""
        logger.info("Initializing speech processing models...")
        
        # Load Whisper model
        logger.info(f"Loading Whisper model: {settings.whisper_model}")
        self.whisper_model = whisper.load_model(settings.whisper_model)
        
        # Load diarization pipeline
        logger.info(f"Loading diarization pipeline: {settings.diarization_model}")
        try:
            self.diarization_pipeline = Pipeline.from_pretrained(
                settings.diarization_model,
                use_auth_token=settings.huggingface_token
            )
            if torch.cuda.is_available():
                self.diarization_pipeline = self.diarization_pipeline.to(torch.device("cuda"))
        except Exception as e:
            logger.error(f"Failed to load diarization pipeline: {e}")
            self.diarization_pipeline = None
        
        # Load speaker embedding model
        logger.info(f"Loading speaker embedding model: {settings.speaker_embedding_model}")
        try:
            self.embedding_model = PretrainedSpeakerEmbedding(
                settings.speaker_embedding_model,
                use_auth_token=settings.huggingface_token,
                device=torch.device(self.device)
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
        
        logger.info("Speech processing models initialized successfully")
    
    def preprocess_audio(self, audio_data: bytes, original_sample_rate: int = None) -> np.ndarray:
        """Preprocess audio data for processing"""
        try:
            # Convert bytes to numpy array
            if isinstance(audio_data, bytes):
                # Assume 16-bit PCM audio
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                audio_array = audio_array / 32768.0  # Normalize to [-1, 1]
            else:
                audio_array = audio_data
            
            # Resample if necessary
            if original_sample_rate and original_sample_rate != self.sample_rate:
                audio_array = librosa.resample(
                    audio_array, 
                    orig_sr=original_sample_rate, 
                    target_sr=self.sample_rate
                )
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            return np.array([])
    
    async def transcribe_audio(self, audio_data: np.ndarray, language: str = None) -> Dict:
        """Transcribe audio using Whisper"""
        if self.whisper_model is None:
            raise RuntimeError("Whisper model not initialized")
        
        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(
                    audio_data,
                    language=language,
                    word_timestamps=True,
                    verbose=False
                )
            )
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {"text": "", "segments": []}
    
    async def diarize_audio(self, audio_data: np.ndarray) -> Optional[Dict]:
        """Perform speaker diarization using pyannote"""
        if self.diarization_pipeline is None:
            logger.warning("Diarization pipeline not available")
            return None
        
        try:
            # Save audio to temporary file for pyannote
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Convert numpy array to audio file
                torchaudio.save(
                    temp_file.name,
                    torch.tensor(audio_data).unsqueeze(0),
                    self.sample_rate
                )
                temp_path = temp_file.name
            
            try:
                # Run diarization in thread pool
                loop = asyncio.get_event_loop()
                diarization = await loop.run_in_executor(
                    None,
                    lambda: self.diarization_pipeline(temp_path)
                )
                
                # Convert to dictionary format
                segments = []
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    segments.append({
                        "start": turn.start,
                        "end": turn.end,
                        "speaker": speaker
                    })
                
                return {"segments": segments}
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error in speaker diarization: {e}")
            return None
    
    def align_transcription_with_diarization(
        self, 
        transcription: Dict, 
        diarization: Dict
    ) -> List[SpeakerSegment]:
        """Align transcription segments with speaker diarization"""
        if not diarization or not transcription.get("segments"):
            # Fallback: create segments without speaker info
            segments = []
            for i, segment in enumerate(transcription.get("segments", [])):
                segments.append(SpeakerSegment(
                    speaker_id=f"Speaker_1",
                    start_time=segment.get("start", 0),
                    end_time=segment.get("end", 0),
                    text=segment.get("text", ""),
                    confidence=0.5
                ))
            return segments
        
        aligned_segments = []
        transcription_segments = transcription["segments"]
        diarization_segments = diarization["segments"]
        
        for trans_seg in transcription_segments:
            trans_start = trans_seg["start"]
            trans_end = trans_seg["end"]
            trans_text = trans_seg["text"].strip()
            
            if not trans_text:
                continue
            
            # Find overlapping speaker segment
            best_speaker = "Unknown"
            best_overlap = 0
            
            for diar_seg in diarization_segments:
                diar_start = diar_seg["start"]
                diar_end = diar_seg["end"]
                
                # Calculate overlap
                overlap_start = max(trans_start, diar_start)
                overlap_end = min(trans_end, diar_end)
                overlap_duration = max(0, overlap_end - overlap_start)
                
                if overlap_duration > best_overlap:
                    best_overlap = overlap_duration
                    best_speaker = diar_seg["speaker"]
            
            aligned_segments.append(SpeakerSegment(
                speaker_id=best_speaker,
                start_time=trans_start,
                end_time=trans_end,
                text=trans_text,
                confidence=0.8 if best_overlap > 0 else 0.3
            ))
        
        return aligned_segments
    
    async def get_speaker_embedding(self, audio_data: np.ndarray, start_time: float, end_time: float) -> Optional[np.ndarray]:
        """Extract speaker embedding from audio segment"""
        if self.embedding_model is None:
            return None
        
        try:
            # Extract audio segment
            start_sample = int(start_time * self.sample_rate)
            end_sample = int(end_time * self.sample_rate)
            segment_audio = audio_data[start_sample:end_sample]
            
            if len(segment_audio) < self.sample_rate * 0.5:  # Less than 0.5 seconds
                return None
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                torchaudio.save(
                    temp_file.name,
                    torch.tensor(segment_audio).unsqueeze(0),
                    self.sample_rate
                )
                temp_path = temp_file.name
            
            try:
                # Get embedding
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    lambda: self.embedding_model(temp_path)
                )
                return embedding.cpu().numpy()
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error extracting speaker embedding: {e}")
            return None
    
    def identify_speaker(self, embedding: np.ndarray, threshold: float = 0.8) -> Optional[str]:
        """Identify speaker using known speaker embeddings"""
        if not self.known_speakers or embedding is None:
            return None
        
        try:
            best_match = None
            best_similarity = threshold
            
            for speaker_name, known_embedding in self.known_speakers.items():
                similarity = cosine_similarity(
                    embedding.reshape(1, -1),
                    known_embedding.reshape(1, -1)
                )[0][0]
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = speaker_name
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error identifying speaker: {e}")
            return None
    
    def add_known_speaker(self, name: str, embedding: np.ndarray):
        """Add a known speaker embedding"""
        self.known_speakers[name] = embedding
        logger.info(f"Added known speaker: {name}")
    
    async def process_audio_chunk(
        self, 
        audio_data: bytes, 
        original_sample_rate: int = None,
        language: str = None
    ) -> List[SpeakerSegment]:
        """Process a single audio chunk and return speaker segments"""
        try:
            # Preprocess audio
            audio_array = self.preprocess_audio(audio_data, original_sample_rate)
            
            if len(audio_array) == 0:
                return []
            
            # Transcribe audio
            transcription = await self.transcribe_audio(audio_array, language)
            
            # Perform diarization
            diarization = await self.diarize_audio(audio_array)
            
            # Align transcription with diarization
            segments = self.align_transcription_with_diarization(transcription, diarization)
            
            # Try to identify known speakers
            for segment in segments:
                embedding = await self.get_speaker_embedding(
                    audio_array, 
                    segment.start_time, 
                    segment.end_time
                )
                if embedding is not None:
                    known_speaker = self.identify_speaker(embedding)
                    if known_speaker:
                        segment.speaker_id = known_speaker
            
            return segments
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return []
