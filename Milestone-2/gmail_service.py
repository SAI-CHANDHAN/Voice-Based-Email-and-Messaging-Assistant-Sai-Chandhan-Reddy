"""
Gmail API Service
Handles Gmail OAuth2 authentication, reading, sending, and replying to emails
"""
import os
import base64
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gmail API scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
]

def strip_html_tags(html: str) -> str:
    """Convert HTML to plain text by removing tags"""
    try:
        # First, remove script and style elements entirely
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Replace br, hr tags with newlines
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'<hr\s*/?>', '\n', html, flags=re.IGNORECASE)
        
        # Replace closing p, div, li tags with newlines
        html = re.sub(r'</p>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</div>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</li>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</tr>', '\n', html, flags=re.IGNORECASE)
        html = re.sub(r'</td>', ' ', html, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = re.sub(r'&#\d+;', '', text)  # Remove numeric entities
        text = re.sub(r'&[a-zA-Z]+;', '', text)  # Remove other named entities
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n+', '\n\n', text)  # Multiple newlines become double newline
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces become single space
        text = re.sub(r' *\n *', '\n', text)  # Remove spaces around newlines
        
        return text.strip()
    except Exception as e:
        logger.warning(f"Failed to parse HTML: {e}")
        # Fallback: simple regex-based tag removal
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

class GmailService:
    """
    Gmail API service for email operations
    """
    
    def __init__(self, credentials: Optional[Credentials] = None):
        """
        Initialize Gmail service
        
        Args:
            credentials: Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = None
        
        if credentials:
            self._build_service()
    
    def _build_service(self):
        """Build Gmail API service"""
        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise
    
    def authenticate(self, token_data: Dict[str, Any]) -> bool:
        """
        Authenticate with Gmail using token data
        
        Args:
            token_data: OAuth2 token dictionary
        
        Returns:
            True if successful
        """
        try:
            # Stored token key is 'token' (access_token); fall back to 'access_token' if present
            access_token = token_data.get('token') or token_data.get('access_token')

            self.credentials = Credentials(
                token=access_token,
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=os.environ.get('GOOGLE_CLIENT_ID'),
                client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
                scopes=GMAIL_SCOPES
            )
            
            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            
            self._build_service()
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    def get_messages(
        self,
        max_results: int = 10,
        query: str = '',
        label_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of messages from Gmail using batch requests for faster loading
        
        Args:
            max_results: Maximum number of messages to return
            query: Gmail search query (e.g., 'is:unread', 'from:user@example.com')
            label_ids: List of label IDs to filter by
        
        Returns:
            List of message dictionaries
        """
        try:
            if not self.service:
                raise ValueError("Gmail service not initialized")

            query_lower = (query or '').lower()

            # Build labelIds parameter. Default to INBOX only when no query/label provided.
            if label_ids is not None:
                list_kwargs = {'labelIds': label_ids}
            elif 'in:trash' in query_lower:
                # For trash, don't use labelIds—let the query handle it and use includeSpamTrash
                list_kwargs = {}
            elif 'in:sent' in query_lower:
                list_kwargs = {}
            elif 'in:draft' in query_lower:
                list_kwargs = {}
            elif query_lower:
                list_kwargs = {}
            else:
                list_kwargs = {'labelIds': ['INBOX']}

            # Allow trash searches by enabling includeSpamTrash when needed
            include_spam_trash = False
            if 'in:trash' in query_lower or (label_ids and any(l.upper() == 'TRASH' for l in label_ids)):
                include_spam_trash = True

            logger.info(
                "Fetching messages with query: %s, labelIds: %s, includeSpamTrash: %s",
                query,
                list_kwargs.get('labelIds', 'None'),
                include_spam_trash,
            )

            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query,
                includeSpamTrash=include_spam_trash,
                **list_kwargs
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(
                "Got %s message IDs (result keys: %s)",
                len(messages),
                list(results.keys()),
            )
            
            # Use batch requests for faster loading (much faster than sequential calls)
            detailed_messages = self._get_messages_batch([msg['id'] for msg in messages])
            
            logger.info(f"Retrieved {len(detailed_messages)} messages")
            return detailed_messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    def _get_messages_batch(self, message_ids: List[str], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch multiple messages using batch requests for better performance
        
        Args:
            message_ids: List of message IDs to fetch
            batch_size: Number of messages per batch (max 10 per Google API limits)
        
        Returns:
            List of message dictionaries
        """
        detailed_messages = []
        
        # Process messages in batches for better performance
        for i in range(0, len(message_ids), batch_size):
            batch = message_ids[i:i + batch_size]
            batch_request = self.service.new_batch_http_request()
            
            message_dict = {}
            
            def callback(request_id, response, exception):
                if exception is not None:
                    logger.error(f"Batch request error: {exception}")
                else:
                    parsed = self._parse_message(response)
                    message_dict[request_id] = parsed
            
            # Add all requests in this batch
            for msg_id in batch:
                batch_request.add(
                    self.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ),
                    request_id=msg_id,
                    callback=callback
                )
            
            # Execute the batch request
            try:
                batch_request.execute()
                # Messages are added via callback
                for msg_id in batch:
                    if msg_id in message_dict:
                        detailed_messages.append(message_dict[msg_id])
            except Exception as e:
                logger.error(f"Batch execution error: {e}")
                # Fallback to sequential requests for this batch
                for msg_id in batch:
                    msg_detail = self.get_message(msg_id)
                    if msg_detail:
                        detailed_messages.append(msg_detail)
        
        return detailed_messages
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed message by ID
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            Message dictionary with parsed data
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Parse message
            parsed = self._parse_message(message)
            return parsed
            
        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None
    
    def _parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message to extract useful information"""
        headers = message['payload']['headers']
        
        # Extract headers
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        to_email = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
        
        # Extract body (prefer plain text over HTML for cleaner display)
        text_body, html_body = self._extract_bodies(message['payload'])
        
        # If we only have HTML, convert it to plain text
        if not text_body and html_body:
            text_body = strip_html_tags(html_body)
        
        body = text_body or html_body
        
        # Extract snippet
        snippet = message.get('snippet', '')
        
        # Check if unread
        is_unread = 'UNREAD' in message.get('labelIds', [])
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': subject,
            'from': from_email,
            'to': to_email,
            'date': date,
            'body': body,
            'body_text': text_body,
            'body_html': html_body,
            'snippet': snippet,
            'is_unread': is_unread,
            'labels': message.get('labelIds', [])
        }

    def _decode_part_body(self, part: Dict[str, Any]) -> str:
        data = part.get('body', {}).get('data', '')
        if not data:
            return ''
        try:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        except Exception:
            return ''

    def _extract_bodies(self, payload: Dict[str, Any]) -> tuple[str, str]:
        """Recursively extract text/plain and text/html bodies."""
        text_body = ''
        html_body = ''

        if not payload:
            return text_body, html_body

        mime_type = payload.get('mimeType', '')

        # Direct body at this level
        if mime_type == 'text/plain':
            text_body = self._decode_part_body(payload)
        elif mime_type == 'text/html':
            html_body = self._decode_part_body(payload)

        # Explore subparts (multipart/*)
        for part in (payload.get('parts') or []):
            t, h = self._extract_bodies(part)
            if t and len(t) > len(text_body):
                text_body = t
            if h and len(h) > len(html_body):
                html_body = h

        # Fallback: decode body if present but unknown type
        if not text_body and not html_body and payload.get('body', {}).get('data'):
            decoded = self._decode_part_body(payload)
            if 'html' in mime_type:
                html_body = decoded
            else:
                text_body = decoded

        return text_body, html_body

    def _get_message_body(self, payload: Dict[str, Any]) -> str:
        """Backwards-compatible: return preferred body (HTML if available)."""
        text_body, html_body = self._extract_bodies(payload)
        return html_body or text_body
    
    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send an email message
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
        
        Returns:
            Sent message details or None if failed
        """
        try:
            # Create message
            message = MIMEMultipart()
            message['To'] = to
            message['Subject'] = subject
            
            if cc:
                message['Cc'] = cc
            if bcc:
                message['Bcc'] = bcc
            
            message.attach(MIMEText(body, 'plain'))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"Email sent successfully: {sent_message['id']}")
            return sent_message
            
        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            return None
    
    def reply_to_message(
        self,
        message_id: str,
        reply_body: str
    ) -> Optional[Dict[str, Any]]:
        """
        Reply to a message
        
        Args:
            message_id: ID of message to reply to
            reply_body: Reply text
        
        Returns:
            Sent reply details or None if failed
        """
        try:
            # Get original message
            original = self.get_message(message_id)
            if not original:
                raise ValueError("Original message not found")
            
            # Extract reply-to address
            reply_to = original['from']
            subject = original['subject']
            if not subject.startswith('Re: '):
                subject = f"Re: {subject}"
            
            # Create reply
            message = MIMEMultipart()
            message['To'] = reply_to
            message['Subject'] = subject
            message['In-Reply-To'] = message_id
            message['References'] = message_id
            
            message.attach(MIMEText(reply_body, 'plain'))
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_reply = self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': original['thread_id']
                }
            ).execute()
            
            logger.info(f"Reply sent successfully: {sent_reply['id']}")
            return sent_reply
            
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            return None
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark message as read
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            True if successful
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Message {message_id} marked as read")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to mark as read: {e}")
            return False
    
    def delete_message(self, message_id: str) -> bool:
        """
        Move message to trash
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            True if successful
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            
            logger.info(f"Message {message_id} moved to trash")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to delete message: {e}")
            return False
    
    def search_messages(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search messages with Gmail query syntax
        
        Args:
            query: Gmail search query
            max_results: Maximum results
        
        Returns:
            List of matching messages
        """
        return self.get_messages(max_results=max_results, query=query)
    
    def get_unread_count(self) -> int:
        """
        Get count of unread messages
        
        Returns:
            Number of unread messages
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1
            ).execute()
            
            return results.get('resultSizeEstimate', 0)
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get Gmail user profile
        
        Returns:
            User profile information
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                'email': profile.get('emailAddress'),
                'messages_total': profile.get('messagesTotal', 0),
                'threads_total': profile.get('threadsTotal', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None


def create_gmail_oauth_flow(redirect_uri: str) -> Flow:
    """
    Create Gmail OAuth flow with timeout and retry configuration
    
    Args:
        redirect_uri: OAuth redirect URI
    
    Returns:
        OAuth Flow object
    """
    client_config = {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=redirect_uri
    )
    
    # Disable scope change warnings - Google may return additional scopes
    # like openid, userinfo.profile, userinfo.email which is fine
    flow.oauth2session._client.scope = None
    
    # Configure session with timeout and retry strategy
    session = requests.Session()
    
    # Retry strategy: retry on connection errors, with exponential backoff
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Set timeout for all requests (30 seconds connect, 30 seconds read)
    original_request = session.request
    def request_with_timeout(*args, **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (30, 30)  # (connect timeout, read timeout)
        return original_request(*args, **kwargs)
    
    session.request = request_with_timeout
    
    # Apply configured session to the OAuth2Session
    flow.oauth2session._client._session = session
    
    return flow
