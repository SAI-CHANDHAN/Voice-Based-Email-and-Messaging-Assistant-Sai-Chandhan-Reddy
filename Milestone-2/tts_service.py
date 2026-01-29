"""
Text-to-Speech (TTS) Service
Provides voice synthesis for reading emails and providing feedback
"""
import os
import logging
from typing import Optional, Dict, Any
from enum import Enum
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    """TTS engine options"""
    PYTTSX3 = "pyttsx3"  # Offline, cross-platform
    GTTS = "gtts"  # Google TTS (requires internet)
    WEB = "web"  # Browser-based Web Speech API

class TTSService:
    """
    Text-to-Speech service with multiple engine support
    """
    
    def __init__(self, engine_type: str = "pyttsx3"):
        """
        Initialize TTS service
        
        Args:
            engine_type: TTS engine to use (pyttsx3, gtts, web)
        """
        self.engine_type = engine_type
        self.engine = None
        self.is_speaking = False
        self.speech_queue = queue.Queue()
        
        # Voice settings (can be customized per user)
        self.rate = 150  # Words per minute
        self.volume = 0.9  # 0.0 to 1.0
        self.voice_id = None  # Specific voice ID
        
        if engine_type == "pyttsx3":
            self._init_pyttsx3()
        
        logger.info(f"TTSService initialized with {engine_type} engine")
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 engine"""
        try:
            import pyttsx3
            
            self.engine = pyttsx3.init()
            
            # Set default properties
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
            
            # Get available voices
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to set a pleasant default voice
                # Prefer female voices or voices with "en" in the name
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.voice_id = voice.id
                        self.engine.setProperty('voice', voice.id)
                        break
                
                if not self.voice_id and voices:
                    self.voice_id = voices[0].id
                    self.engine.setProperty('voice', voices[0].id)
            
            logger.info("pyttsx3 engine initialized successfully")
            
        except ImportError:
            logger.warning("pyttsx3 not installed. Run: pip install pyttsx3")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
    
    def speak(self, text: str, async_mode: bool = False) -> bool:
        """
        Speak the given text
        
        Args:
            text: Text to speak
            async_mode: If True, speak asynchronously without blocking
        
        Returns:
            True if successful
        """
        if not text or not text.strip():
            return False
        
        try:
            if self.engine_type == "pyttsx3":
                return self._speak_pyttsx3(text, async_mode)
            elif self.engine_type == "gtts":
                return self._speak_gtts(text)
            else:
                logger.warning(f"Unsupported TTS engine: {self.engine_type}")
                return False
                
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return False
    
    def _speak_pyttsx3(self, text: str, async_mode: bool) -> bool:
        """Speak using pyttsx3"""
        if not self.engine:
            logger.error("pyttsx3 engine not initialized")
            return False
        
        try:
            # Stop any ongoing speech before starting new one
            if self.is_speaking:
                logger.info("Stopping previous speech before starting new one")
                try:
                    self.engine.stop()
                except:
                    pass
                self.is_speaking = False
            
            if async_mode:
                # Speak in background thread
                thread = threading.Thread(target=self._speak_thread, args=(text,))
                thread.daemon = True
                thread.start()
                logger.info(f"Started async speech thread for: {text[:50]}...")
            else:
                # Blocking speech
                self.is_speaking = True
                logger.info(f"Speaking synchronously: {text[:50]}...")
                self.engine.say(text)
                self.engine.runAndWait()
                self.is_speaking = False
            
            return True
            
        except Exception as e:
            logger.error(f"pyttsx3 speech failed: {e}", exc_info=True)
            self.is_speaking = False
            return False
    
    def _speak_thread(self, text: str):
        """Background thread for async speech"""
        try:
            logger.info(f"Async speech thread started, speaking: {text[:50]}...")
            self.is_speaking = True
            # Create a new engine instance for this thread to avoid thread safety issues
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', self.rate)
            engine.setProperty('volume', self.volume)
            if self.voice_id:
                engine.setProperty('voice', self.voice_id)
            
            engine.say(text)
            engine.runAndWait()
            engine.stop()  # Clean up engine
            logger.info("Async speech completed successfully")
        except Exception as e:
            logger.error(f"Async speech failed: {e}", exc_info=True)
        finally:
            self.is_speaking = False
    
    def _speak_gtts(self, text: str) -> bool:
        """Speak using Google TTS"""
        try:
            from gtts import gTTS
            import tempfile
            import os
            import platform
            
            # Create speech
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_path = fp.name
                tts.save(temp_path)
            
            # Play audio
            if platform.system() == 'Darwin':  # macOS
                os.system(f'afplay {temp_path}')
            elif platform.system() == 'Windows':
                os.system(f'start {temp_path}')
            else:  # Linux
                os.system(f'mpg321 {temp_path}')
            
            # Clean up
            try:
                os.remove(temp_path)
            except:
                pass
            
            return True
            
        except ImportError:
            logger.warning("gTTS not installed. Run: pip install gtts")
            return False
        except Exception as e:
            logger.error(f"gTTS failed: {e}")
            return False
    
    def read_email(self, email_data: Dict[str, Any], include_body: bool = True) -> bool:
        """
        Read email aloud with natural formatting
        
        Args:
            email_data: Email dictionary with subject, from, date, body
            include_body: Whether to read the full body
        
        Returns:
            True if successful
        """
        try:
            # Build natural speech text
            parts = []
            
            # Subject
            subject = email_data.get('subject', 'No Subject')
            parts.append(f"Email subject: {subject}")
            
            # From
            from_address = email_data.get('from', 'Unknown sender')
            # Extract name if available
            from_name = self._extract_name_from_email(from_address)
            parts.append(f"From: {from_name}")
            
            # Date (simplified)
            date_str = email_data.get('date', '')
            if date_str:
                parts.append(f"Received: {self._format_date_for_speech(date_str)}")
            
            # Body
            if include_body:
                body = email_data.get('body') or email_data.get('snippet', '')
                if body:
                    # Clean up body for speech - this will remove all HTML tags
                    clean_body = self._clean_text_for_speech(body)
                    
                    # Limit length for readability
                    max_length = 800  # Increased to get more content
                    if len(clean_body) > max_length:
                        clean_body = clean_body[:max_length] + "... Message continues."
                    
                    # Only add if there's meaningful content
                    if clean_body and clean_body.strip():
                        parts.append(f"Message: {clean_body}")
                    else:
                        parts.append("Message: Empty or unreadable email")
            else:
                snippet = email_data.get('snippet', '')
                if snippet:
                    clean_snippet = self._clean_text_for_speech(snippet)
                    parts.append(f"Preview: {clean_snippet}")
            
            # Combine and speak
            full_text = ". ".join(parts)
            logger.info(f"Reading email aloud: {full_text[:100]}...")
            logger.info(f"Full email text to speak: {full_text}")
            # Use async_mode=True for non-blocking speech
            result = self.speak(full_text, async_mode=True)
            logger.info(f"Speak result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to read email: {e}")
            return False
    
    def _extract_name_from_email(self, email_str: str) -> str:
        """Extract name from email string like 'John Doe <john@example.com>'"""
        import re
        
        # Try to extract name before email
        match = re.match(r'^([^<]+)<.+>$', email_str)
        if match:
            return match.group(1).strip().strip('"\'')
        
        # If no name, return email
        return email_str
    
    def _format_date_for_speech(self, date_str: str) -> str:
        """Format date string for natural speech"""
        # Simplify date for speech
        # You could use dateutil.parser for better parsing
        try:
            from datetime import datetime
            # Basic parsing - this could be improved
            if ',' in date_str:
                date_str = date_str.split(',')[1].strip()
            return date_str.split(' ')[0:3]  # Just get first few parts
        except:
            return "recently"
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text to make it more suitable for speech"""
        import re
        from html import unescape
        
        # Unescape HTML entities (&#8199; etc)
        text = unescape(text)
        
        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # Remove script and style tags and their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove title tags and content
        text = re.sub(r'<title[^>]*>.*?</title>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://\S+', 'link', text)
        
        # Remove email addresses (replace with "email address")
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email address', text)
        
        # Remove special Unicode characters that don't read well
        text = re.sub(r'[^\w\s.,!?;:\-\'\n]', '', text)
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def set_voice_properties(self, rate: Optional[int] = None, volume: Optional[float] = None, voice_id: Optional[str] = None):
        """
        Update voice properties
        
        Args:
            rate: Speech rate (words per minute)
            volume: Volume (0.0 to 1.0)
            voice_id: Specific voice identifier
        """
        if not self.engine:
            logger.warning("Engine not initialized")
            return
        
        try:
            if rate is not None:
                self.rate = rate
                self.engine.setProperty('rate', rate)
            
            if volume is not None:
                self.volume = volume
                self.engine.setProperty('volume', volume)
            
            if voice_id is not None:
                self.voice_id = voice_id
                self.engine.setProperty('voice', voice_id)
            
            logger.info(f"Voice properties updated: rate={self.rate}, volume={self.volume}")
            
        except Exception as e:
            logger.error(f"Failed to set voice properties: {e}")
    
    def get_available_voices(self) -> list:
        """
        Get list of available voices
        
        Returns:
            List of voice dictionaries with id, name, and languages
        """
        if not self.engine or self.engine_type != "pyttsx3":
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [
                {
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages
                }
                for voice in voices
            ]
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []
    
    def stop(self):
        """Stop current speech"""
        if self.engine and self.engine_type == "pyttsx3":
            try:
                self.engine.stop()
                self.is_speaking = False
            except Exception as e:
                logger.error(f"Failed to stop speech: {e}")
    
    def is_busy(self) -> bool:
        """Check if TTS is currently speaking"""
        return self.is_speaking


# Singleton instance
_tts_service = None

def get_tts_service(engine: str = None) -> TTSService:
    """
    Get or create TTS service instance
    
    Args:
        engine: TTS engine type (if creating new instance)
    
    Returns:
        TTSService instance
    """
    global _tts_service
    
    if _tts_service is None:
        engine = engine or os.environ.get('TTS_ENGINE', 'pyttsx3')
        _tts_service = TTSService(engine)
    
    return _tts_service
