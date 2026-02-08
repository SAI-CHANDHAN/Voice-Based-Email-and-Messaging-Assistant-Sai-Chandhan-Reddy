"""
Speech Recognition Service
Supports multiple STT engines: Whisper (cloud/local), Vosk (offline), and Google STT
"""
import os
import io
import wave
import json
import logging
from typing import Optional, Dict, Any
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class STTEngine(Enum):
    """Speech-to-Text engine options"""
    WHISPER = "whisper"
    VOSK = "vosk"
    GOOGLE = "google"
    WEB = "web"  # Browser-based Web Speech API

class SpeechRecognitionService:
    """
    Unified speech recognition service supporting multiple STT engines
    """
    
    def __init__(self, preferred_engine: str = "whisper"):
        """
        Initialize speech recognition service
        
        Args:
            preferred_engine: Preferred STT engine (whisper, vosk, google)
        """
        self.preferred_engine = preferred_engine
        self.whisper_model = None
        self.vosk_model = None
        
        # Initialize engines based on preference
        if preferred_engine == "whisper":
            self._init_whisper()
        elif preferred_engine == "vosk":
            self._init_vosk()
        
        logger.info(f"SpeechRecognitionService initialized with {preferred_engine} engine")
    
    def _init_whisper(self):
        """Initialize Whisper model"""
        try:
            import whisper
            # Load base model for balance between speed and accuracy
            # Options: tiny, base, small, medium, large
            model_size = os.environ.get('WHISPER_MODEL_SIZE', 'base')
            self.whisper_model = whisper.load_model(model_size)
            logger.info(f"Whisper model '{model_size}' loaded successfully")
        except ImportError:
            logger.warning("Whisper not installed. Run: pip install openai-whisper")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")
    
    def _init_vosk(self):
        """Initialize Vosk model"""
        try:
            from vosk import Model, KaldiRecognizer
            
            # Check for model path in environment or use default
            model_path = os.environ.get('VOSK_MODEL_PATH', 'models/vosk-model-small-en-us-0.15')
            
            if not os.path.exists(model_path):
                logger.warning(f"Vosk model not found at {model_path}")
                logger.info("Download models from: https://alphacephei.com/vosk/models")
                return
            
            self.vosk_model = Model(model_path)
            logger.info(f"Vosk model loaded from {model_path}")
        except ImportError:
            logger.warning("Vosk not installed. Run: pip install vosk")
        except Exception as e:
            logger.error(f"Failed to initialize Vosk: {e}")
    
    def transcribe_audio_file(self, audio_file_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio from file using preferred engine with fallback
        
        Args:
            audio_file_path: Path to audio file
            language: Language code (default: en)
        
        Returns:
            Dictionary with transcription result and metadata
        """
        try:
            # Try preferred engine first
            if self.preferred_engine == "whisper" and self.whisper_model:
                return self._transcribe_with_whisper(audio_file_path, language)
            elif self.preferred_engine == "vosk" and self.vosk_model:
                return self._transcribe_with_vosk(audio_file_path)
            
            # Fallback to Google STT
            return self._transcribe_with_google(audio_file_path, language)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "engine": self.preferred_engine
            }
    
    def _transcribe_with_whisper(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe using Whisper"""
        try:
            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                fp16=False  # Disable FP16 for CPU compatibility
            )
            
            return {
                "success": True,
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "engine": "whisper",
                "confidence": None  # Whisper doesn't provide confidence scores
            }
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise
    
    def _transcribe_with_vosk(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe using Vosk"""
        try:
            from vosk import KaldiRecognizer
            
            # Open audio file
            wf = wave.open(audio_path, "rb")
            
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in [8000, 16000, 32000, 44100, 48000]:
                logger.error("Audio file must be WAV format mono PCM.")
                raise ValueError("Invalid audio format")
            
            # Create recognizer
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
            rec.SetWords(True)
            
            # Process audio
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    results.append(result.get("text", ""))
            
            # Final result
            final_result = json.loads(rec.FinalResult())
            results.append(final_result.get("text", ""))
            
            text = " ".join(results).strip()
            
            return {
                "success": True,
                "text": text,
                "engine": "vosk",
                "confidence": final_result.get("confidence", None)
            }
        except Exception as e:
            logger.error(f"Vosk transcription failed: {e}")
            raise
        finally:
            if 'wf' in locals():
                wf.close()
    
    def _transcribe_with_google(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe using Google Speech Recognition"""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            with sr.AudioFile(audio_path) as source:
                audio_data = recognizer.record(source)
            
            # Use Google Speech Recognition API
            text = recognizer.recognize_google(audio_data, language=language)
            
            return {
                "success": True,
                "text": text,
                "engine": "google",
                "confidence": None
            }
        except Exception as e:
            logger.error(f"Google STT failed: {e}")
            raise
    
    def transcribe_audio_data(self, audio_data: bytes, format: str = "wav", language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio from binary data
        
        Args:
            audio_data: Binary audio data
            format: Audio format (wav, mp3, etc.)
            language: Language code
        
        Returns:
            Transcription result
        """
        import tempfile
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=f'.{format}', delete=False) as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        try:
            result = self.transcribe_audio_file(tmp_path, language)
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    def get_available_engines(self) -> list:
        """Get list of available STT engines"""
        engines = []
        
        if self.whisper_model:
            engines.append("whisper")
        if self.vosk_model:
            engines.append("vosk")
        
        # Google is always available (requires internet)
        engines.append("google")
        
        return engines
    
    def switch_engine(self, engine: str):
        """
        Switch to a different STT engine
        
        Args:
            engine: Engine name (whisper, vosk, google)
        """
        if engine not in ["whisper", "vosk", "google"]:
            raise ValueError(f"Invalid engine: {engine}")
        
        self.preferred_engine = engine
        
        # Initialize if not already done
        if engine == "whisper" and not self.whisper_model:
            self._init_whisper()
        elif engine == "vosk" and not self.vosk_model:
            self._init_vosk()
        
        logger.info(f"Switched to {engine} engine")


# Singleton instance
_speech_service = None

def get_speech_service(engine: str = None) -> SpeechRecognitionService:
    """
    Get or create speech recognition service instance
    
    Args:
        engine: Preferred engine (if creating new instance)
    
    Returns:
        SpeechRecognitionService instance
    """
    global _speech_service
    
    if _speech_service is None:
        engine = engine or os.environ.get('STT_ENGINE', 'whisper')
        _speech_service = SpeechRecognitionService(engine)
    
    return _speech_service
