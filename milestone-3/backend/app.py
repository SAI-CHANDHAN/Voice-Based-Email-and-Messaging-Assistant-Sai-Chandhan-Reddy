"""
Telegram Backend API for Voice-Based Messaging Assistant
Handles Telegram authentication and message operations using Telethon
"""

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_session import Session
from telethon import TelegramClient
import os
import logging
from dotenv import load_dotenv
import asyncio
import threading

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-telegram')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False

# Enable CORS for React frontend
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://localhost:3000"])
Session(app)

# Telegram configuration
API_ID = int(os.getenv('VITE_TELEGRAM_API_ID', 0))
API_HASH = os.getenv('VITE_TELEGRAM_API_HASH', '')
PHONE_NUMBER = os.getenv('VITE_TELEGRAM_PHONE_NUMBER', '')
SESSION_NAME = os.getenv('VITE_TELEGRAM_SESSION_NAME', 'telegram_session')

# Dedicated thread and event loop for Telegram
telegram_loop = None
telegram_thread = None
telegram_clients = {}

# Ensure sessions directory exists
os.makedirs('sessions', exist_ok=True)

def init_telegram_loop():
    """Initialize the dedicated event loop for Telegram in a separate thread"""
    global telegram_loop, telegram_thread
    
    def run_loop():
        global telegram_loop
        telegram_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(telegram_loop)
        logger.info("[TELEGRAM] Event loop started in dedicated thread")
        telegram_loop.run_forever()
    
    telegram_thread = threading.Thread(target=run_loop, daemon=True)
    telegram_thread.start()
    
    # Wait for loop to be created
    import time
    while telegram_loop is None:
        time.sleep(0.01)
    
    logger.info("[TELEGRAM] Dedicated event loop ready")

def run_async(coro):
    """Run async function in the dedicated Telegram loop"""
    if telegram_loop is None:
        init_telegram_loop()
    
    future = asyncio.run_coroutine_threadsafe(coro, telegram_loop)
    return future.result(timeout=60)  # 60 second timeout

def get_client(user_id='default'):
    """Get or create Telegram client for user"""
    if user_id not in telegram_clients:
        telegram_clients[user_id] = TelegramClient(
            f'sessions/{SESSION_NAME}_{user_id}',
            API_ID,
            API_HASH
        )
    return telegram_clients[user_id]

@app.route('/api/telegram/connect', methods=['POST'])
def connect_telegram():
    """Connect to Telegram"""
    async def _connect():
        try:
            data = request.json
            api_id = int(data.get('apiId', API_ID))
            api_hash = data.get('apiHash', API_HASH)
            phone = data.get('phoneNumber', PHONE_NUMBER)
            
            if not api_id or not api_hash or not phone:
                return {
                    'success': False,
                    'error': 'Missing API credentials'
                }, 400
            
            client = get_client('default')
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                # Send code request
                await client.send_code_request(phone)
                session['telegram_phone'] = phone
                session['telegram_api_id'] = api_id
                session['telegram_api_hash'] = api_hash
                
                return {
                    'success': True,
                    'needsCode': True,
                    'message': 'Verification code sent to your Telegram'
                }, 200
            
            return {
                'success': True,
                'needsCode': False,
                'message': 'Already connected'
            }, 200
            
        except Exception as e:
            logger.error(f"Telegram connection error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_connect())
    return jsonify(result), status_code

@app.route('/api/telegram/verify', methods=['POST'])
def verify_code():
    """Verify Telegram authentication code"""
    async def _verify():
        try:
            data = request.json
            code = data.get('code')
            phone = session.get('telegram_phone')
            
            if not code or not phone:
                return {
                    'success': False,
                    'error': 'Missing code or phone'
                }, 400
            
            client = get_client('default')
            
            logger.info(f"[TELEGRAM] Verifying code for {phone}")
            await client.sign_in(phone, code)
            logger.info("[TELEGRAM] Verification successful")
            
            return {
                'success': True,
                'message': 'Successfully authenticated'
            }, 200
            
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_verify())
    return jsonify(result), status_code

@app.route('/api/telegram/chats', methods=['GET'])
def get_chats():
    """Get list of Telegram chats"""
    async def _get_chats():
        try:
            limit = request.args.get('limit', 20, type=int)
            
            client = get_client('default')
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return {
                    'success': False,
                    'error': 'Not authorized'
                }, 401
            
            dialogs = await client.get_dialogs(limit=limit)
            
            chats = []
            for dialog in dialogs:
                chat_data = {
                    'id': dialog.id,
                    'title': dialog.title or dialog.name,
                    'isPrivate': dialog.is_user,
                    'isSupergroup': dialog.is_group,
                    'unreadCount': dialog.unread_count,
                    'lastMessage': dialog.message.text if dialog.message else None,
                }
                chats.append(chat_data)
            
            logger.info(f"[TELEGRAM] Fetched {len(chats)} chats")
            return {
                'success': True,
                'chats': chats
            }, 200
            
        except Exception as e:
            logger.error(f"Error fetching chats: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_get_chats())
    return jsonify(result), status_code

@app.route('/api/telegram/messages/<chat_id>', methods=['GET'])
def get_messages(chat_id):
    """Get messages from a specific chat"""
    async def _get_messages():
        try:
            # Parse chat_id manually to handle negative IDs
            try:
                chat_id_int = int(chat_id)
            except ValueError:
                return {
                    'success': False,
                    'error': 'Invalid chat ID'
                }, 400
            
            limit = request.args.get('limit', 50, type=int)
            
            client = get_client('default')
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return {
                    'success': False,
                    'error': 'Not authorized'
                }, 401
            
            messages = await client.get_messages(chat_id_int, limit=limit)
            
            message_list = []
            for msg in messages:
                message_data = {
                    'id': msg.id,
                    'senderId': msg.sender_id,
                    'text': msg.text or '',
                    'date': msg.date.isoformat(),
                    'chatId': chat_id_int,
                    'senderName': None,
                    'fromSelf': msg.out,
                }
                
                # Get sender name
                if msg.sender:
                    try:
                        if hasattr(msg.sender, 'first_name'):
                            message_data['senderName'] = msg.sender.first_name
                            if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                                message_data['senderName'] += f" {msg.sender.last_name}"
                        elif hasattr(msg.sender, 'title'):
                            message_data['senderName'] = msg.sender.title
                    except:
                        pass
                
                message_list.append(message_data)
            
            return {
                'success': True,
                'messages': message_list
            }, 200
            
        except Exception as e:
            logger.error(f"Error fetching messages: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_get_messages())
    return jsonify(result), status_code

@app.route('/api/telegram/send', methods=['POST'])
def send_message():
    """Send a message to a chat"""
    async def _send():
        try:
            data = request.json
            chat_id = data.get('chatId')
            text = data.get('text')
            
            if not chat_id or not text:
                return {
                    'success': False,
                    'error': 'Missing chatId or text'
                }, 400
            
            client = get_client('default')
            
            if not client.is_connected():
                await client.connect()
            
            if not await client.is_user_authorized():
                return {
                    'success': False,
                    'error': 'Not authorized'
                }, 401
            
            message = await client.send_message(chat_id, text)
            
            return {
                'success': True,
                'messageId': message.id,
                'message': 'Message sent successfully'
            }, 200
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_send())
    return jsonify(result), status_code

@app.route('/api/telegram/disconnect', methods=['POST'])
def disconnect_telegram():
    """Disconnect from Telegram"""
    async def _disconnect():
        try:
            client = get_client('default')
            await client.disconnect()
            
            return {
                'success': True,
                'message': 'Disconnected successfully'
            }, 200
            
        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    result, status_code = run_async(_disconnect())
    return jsonify(result), status_code

@app.route('/api/telegram/status', methods=['GET'])
def telegram_status():
    """Get Telegram connection status and auto-reconnect if session exists"""
    async def _status():
        try:
            client = get_client('default')
            
            # Auto-reconnect if not connected but session exists
            if not client.is_connected():
                session_file = f'sessions/{SESSION_NAME}_default.session'
                if os.path.exists(session_file):
                    logger.info("[TELEGRAM] Session file found, reconnecting...")
                    try:
                        await client.connect()
                        logger.info("[TELEGRAM] Reconnected using existing session")
                    except Exception as e:
                        logger.error(f"[TELEGRAM] Reconnection failed: {str(e)}")
                        return {
                            'success': True,
                            'connected': False,
                            'authorized': False,
                        }, 200
                else:
                    return {
                        'success': True,
                        'connected': False,
                        'authorized': False,
                    }, 200
            
            is_authorized = await client.is_user_authorized()
            
            return {
                'success': True,
                'connected': True,
                'authorized': is_authorized,
            }, 200
            
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return {
                'success': True,
                'connected': False,
                'authorized': False,
            }, 200
    
    result, status_code = run_async(_status())
    return jsonify(result), status_code

if __name__ == '__main__':
    print("=" * 60)
    print("Telegram Backend API Starting...")
    print(f"API ID: {API_ID}")
    print(f"Phone: {PHONE_NUMBER}")
    print("=" * 60)
    
    # Initialize the dedicated Telegram event loop
    init_telegram_loop()
    
    # Start Flask app
    app.run(debug=True, port=5001, host='0.0.0.0', threaded=True)
