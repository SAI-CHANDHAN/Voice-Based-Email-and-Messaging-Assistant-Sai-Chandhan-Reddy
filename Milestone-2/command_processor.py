"""
Natural Language Understanding (NLU) Command Processor
Uses Hugging Face Transformers for intent recognition and entity extraction
"""
import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Intent(Enum):
    """Command intents"""
    # Email commands
    READ_EMAIL = "read_email"
    SEND_EMAIL = "send_email"
    REPLY_EMAIL = "reply_email"
    DELETE_EMAIL = "delete_email"
    SEARCH_EMAIL = "search_email"
    
    # Email navigation
    SENT_EMAIL = "sent_email"
    DELETED_EMAIL = "deleted_email"
    OPEN_EMAIL = "open_email"
    
    # General commands
    HELP = "help"
    STATUS = "status"
    SETTINGS = "settings"
    LOGOUT = "logout"
    
    # Unknown
    UNKNOWN = "unknown"

@dataclass
class CommandResult:
    """Result of command processing"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    original_text: str
    action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "original_text": self.original_text,
            "action": self.action
        }

class CommandProcessor:
    """
    Process natural language commands using pattern matching and NLU
    """
    
    def __init__(self, use_transformer: bool = False):
        """
        Initialize command processor
        
        Args:
            use_transformer: Whether to use transformer-based NLU (requires more resources)
        """
        self.use_transformer = use_transformer
        self.pipeline = None
        
        # Email patterns
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Command patterns for rule-based matching
        self.intent_patterns = {
            Intent.READ_EMAIL: [
                r'read\s+(my\s+)?(email|emails|mail|messages?)',
                r'check\s+(my\s+)?(email|emails|inbox)',
                r'show\s+(me\s+)?(my\s+)?(email|emails|messages?)',
                r'what\s+emails?\s+do\s+i\s+have',
                r'any\s+new\s+(email|emails|messages?)',
                r'read\s+(email|mail|message)\s+\d+',
                r'\d+(?:st|nd|rd|th)?\s+(email|mail|message)',
                r'show\s+(me\s+)?(email|mail|message)\s+\d+',
            ],
            Intent.SEND_EMAIL: [
                r'send\s+(an?\s+)?(email|mail|message)',
                r'compose\s+(an?\s+)?(email|mail|message)',
                r'write\s+(an?\s+)?(email|mail|message)',
                r'email\s+to\s+',
            ],
            Intent.REPLY_EMAIL: [
                r'reply\s+(to\s+)?(this\s+)?(email|message)',
                r'reply\s+(to\s+)?(email|message)\s+\d+',
                r'respond\s+(to\s+)?(this\s+)?(email|message)',
                r'answer\s+(this\s+)?(email|message)',
            ],
            Intent.DELETE_EMAIL: [
                r'delete\s+(this\s+)?(email|message)',
                r'delete\s+(email|message)\s+\d+',
                r'remove\s+(this\s+)?(email|message)',
                r'remove\s+(email|message)\s+\d+',
                r'trash\s+(this\s+)?(email|message)',
                r'trash\s+(email|message)\s+\d+',
            ],
            Intent.SEARCH_EMAIL: [
                r'search\s+(for\s+)?(email|emails|messages?)',
                r'find\s+(email|emails|messages?)',
                r'look\s+for\s+(email|emails|messages?)',
            ],
            Intent.SENT_EMAIL: [
                r'sent\s+(email|emails|mail|messages?)',
                r'show\s+sent',
                r'check\s+sent',
                r'my\s+sent',
            ],
            Intent.DELETED_EMAIL: [
                r'deleted\s+(email|emails|messages?)',
                r'trash',
                r'show\s+deleted',
                r'check\s+trash',
            ],
            Intent.HELP: [
                r'help',
                r'what\s+can\s+you\s+do',
                r'how\s+do\s+i',
                r'commands?',
            ],
            Intent.STATUS: [
                r'status',
                r'how\s+many\s+emails?',
                r'email\s+count',
            ],
            Intent.LOGOUT: [
                r'log\s*out',
                r'sign\s*out',
                r'exit',
                r'quit',
            ],
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for intent, patterns in self.intent_patterns.items():
            self.compiled_patterns[intent] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        if use_transformer:
            self._init_transformer()
        
        logger.info(f"CommandProcessor initialized (transformer: {use_transformer})")
    
    def _init_transformer(self):
        """Initialize transformer-based NLU pipeline"""
        try:
            from transformers import pipeline
            
            # Use zero-shot classification for flexible intent recognition
            model_name = os.environ.get('NLU_MODEL', 'facebook/bart-large-mnli')
            self.pipeline = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=-1  # CPU, use 0 for GPU
            )
            logger.info(f"Transformer model loaded: {model_name}")
        except ImportError:
            logger.warning("Transformers not installed. Using rule-based matching only.")
        except Exception as e:
            logger.error(f"Failed to initialize transformer: {e}")
    
    def process_command(self, text: str) -> CommandResult:
        """
        Process a natural language command
        
        Args:
            text: Command text
        
        Returns:
            CommandResult with intent and entities
        """
        text = text.strip()
        
        # Try rule-based matching first (faster)
        intent, confidence = self._match_intent(text)
        
        # If low confidence and transformer available, use it
        if confidence < 0.7 and self.use_transformer and self.pipeline:
            intent, confidence = self._classify_with_transformer(text)
        
        # Extract entities
        entities = self._extract_entities(text, intent)
        
        # Determine action
        action = self._determine_action(intent, entities)
        
        return CommandResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            original_text=text,
            action=action
        )
    
    def _match_intent(self, text: str) -> Tuple[Intent, float]:
        """
        Match intent using rule-based patterns
        
        Returns:
            Tuple of (Intent, confidence)
        """
        text_lower = text.lower()
        
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    return intent, 0.9  # High confidence for exact match
        
        return Intent.UNKNOWN, 0.0
    
    def _classify_with_transformer(self, text: str) -> Tuple[Intent, float]:
        """
        Classify intent using transformer model
        
        Returns:
            Tuple of (Intent, confidence)
        """
        try:
            # Define candidate labels
            candidate_labels = [
                "read emails",
                "send email",
                "reply to email",
                "delete email",
                "search emails",
                "navigate to next",
                "navigate to previous",
                "get help",
                "check status",
                "logout"
            ]
            
            result = self.pipeline(text, candidate_labels)
            
            # Map label to intent
            label_to_intent = {
                "read emails": Intent.READ_EMAIL,
                "send email": Intent.SEND_EMAIL,
                "reply to email": Intent.REPLY_EMAIL,
                "delete email": Intent.DELETE_EMAIL,
                "search emails": Intent.SEARCH_EMAIL,
                "navigate to next": Intent.NEXT_EMAIL,
                "navigate to previous": Intent.PREVIOUS_EMAIL,
                "get help": Intent.HELP,
                "check status": Intent.STATUS,
                "logout": Intent.LOGOUT,
            }
            
            top_label = result['labels'][0]
            confidence = result['scores'][0]
            
            intent = label_to_intent.get(top_label, Intent.UNKNOWN)
            
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Transformer classification failed: {e}")
            return Intent.UNKNOWN, 0.0
    
    def _extract_entities(self, text: str, intent: Intent) -> Dict[str, Any]:
        """
        Extract entities from text based on intent

        Returns:
            Dictionary of entities
        """
        entities = {}
        
        # Extract email number (e.g., "email 1", "1st email", "first email")
        email_num_match = re.search(r'(?:email|mail)\s+(\d+)', text, re.IGNORECASE)
        if email_num_match:
            entities['email_number'] = int(email_num_match.group(1))
        
        # Also check for ordinal patterns (1st, 2nd, 3rd, etc.)
        ordinal_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+(?:email|mail)', text, re.IGNORECASE)
        if ordinal_match and 'email_number' not in entities:
            entities['email_number'] = int(ordinal_match.group(1))
        
        # Extract email addresses
        emails = self.email_pattern.findall(text)
        if emails:
            entities['email_addresses'] = emails
            entities['recipient'] = emails[0]  # Primary recipient
        
        # Extract recipient name (before @)
        to_match = re.search(r'to\s+([a-zA-Z0-9\s]+?)(?:\s+about|\s+regarding|$)', text, re.IGNORECASE)
        if to_match:
            entities['recipient_name'] = to_match.group(1).strip()
        
        # Extract subject
        subject_match = re.search(r'(?:about|regarding|subject)\s+(.+?)(?:\s+saying|\s+with|$)', text, re.IGNORECASE)
        if subject_match:
            entities['subject'] = subject_match.group(1).strip()
        
        # Extract message body
        body_match = re.search(r'(?:saying|message|body)\s+(.+)$', text, re.IGNORECASE)
        if body_match:
            entities['body'] = body_match.group(1).strip()
        
        # Extract search query
        if intent == Intent.SEARCH_EMAIL:
            search_match = re.search(r'(?:for|about)\s+(.+)$', text, re.IGNORECASE)
            if search_match:
                entities['query'] = search_match.group(1).strip()
        
        # Extract count/limit
        count_match = re.search(r'(\d+)\s+(email|message|mail)', text, re.IGNORECASE)
        if count_match:
            entities['count'] = int(count_match.group(1))
        
        # Extract time references
        if any(word in text.lower() for word in ['today', 'yesterday', 'last week', 'this week']):
            entities['time_filter'] = self._extract_time_reference(text)
        
        return entities
    
    def _extract_time_reference(self, text: str) -> str:
        """Extract time reference from text"""
        text_lower = text.lower()
        
        if 'today' in text_lower:
            return 'today'
        elif 'yesterday' in text_lower:
            return 'yesterday'
        elif 'last week' in text_lower:
            return 'last_week'
        elif 'this week' in text_lower:
            return 'this_week'
        elif 'last month' in text_lower:
            return 'last_month'
        
        return 'all'
    
    def _determine_action(self, intent: Intent, entities: Dict[str, Any]) -> Optional[str]:
        """
        Determine specific action based on intent and entities
        
        Returns:
            Action string or None
        """
        action_map = {
            Intent.READ_EMAIL: "fetch_emails",
            Intent.SEND_EMAIL: "compose_email",
            Intent.REPLY_EMAIL: "reply_to_email",
            Intent.DELETE_EMAIL: "delete_email",
            Intent.SEARCH_EMAIL: "search_emails",
            Intent.SENT_EMAIL: "fetch_sent_emails",
            Intent.DELETED_EMAIL: "fetch_deleted_emails",
            Intent.HELP: "show_help",
            Intent.STATUS: "get_status",
            Intent.LOGOUT: "logout_user",
        }
        
        return action_map.get(intent)
    
    def get_command_suggestions(self) -> List[str]:
        """
        Get list of example commands
        
        Returns:
            List of command examples
        """
        return [
            "Read my emails",
            "Send email to john@example.com about project update",
            "Reply to this email",
            "Search emails from last week",
            "Delete this email",
            "Show sent emails",
            "Show deleted emails",
            "How many emails do I have?",
            "Help",
        ]


# Singleton instance
_command_processor = None

def get_command_processor(use_transformer: bool = False) -> CommandProcessor:
    """
    Get or create command processor instance
    
    Args:
        use_transformer: Whether to use transformer-based NLU
    
    Returns:
        CommandProcessor instance
    """
    global _command_processor
    
    if _command_processor is None:
        use_transformer = use_transformer or os.environ.get('USE_TRANSFORMER_NLU', 'false').lower() == 'true'
        _command_processor = CommandProcessor(use_transformer)
    
    return _command_processor
