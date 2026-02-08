"""
Voice-Based Email & Messaging Assistant
Milestone 1: Authentication & Profile Management with Voice Commands
Milestone 2: Speech Recognition & Gmail Integration
"""
import os
import logging
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow OAuth over HTTP during local development (never enable in production).
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
# Relax scope validation so OAuth doesn't fail when Google returns extra scopes
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import speech_recognition as sr
from google_auth_oauthlib.flow import Flow
import requests
from dotenv import load_dotenv
import base64
from sqlalchemy import inspect, text

# Load environment variables
load_dotenv()

# Debug: Print loaded credentials (remove in production)
print("=" * 60)
print("ENVIRONMENT VARIABLES LOADED:")
print(f"  GOOGLE_CLIENT_ID: {'[OK]' if os.environ.get('GOOGLE_CLIENT_ID') else '[MISSING]'}")
print(f"  GOOGLE_CLIENT_SECRET: {'[OK]' if os.environ.get('GOOGLE_CLIENT_SECRET') else '[MISSING]'}")
print(f"  GOOGLE_REDIRECT_URI: {os.environ.get('GOOGLE_REDIRECT_URI', 'NOT FOUND')}")
print("=" * 60)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///voice_assistant.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies with redirects
app.config['SESSION_COOKIE_SECURE'] = False   # Allow HTTP for development
app.config['SESSION_COOKIE_HTTPONLY'] = True

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')

GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

db = SQLAlchemy(app)
Session(app)  # Server-side sessions to keep users logged in
CORS(app)     # Enable cross-origin requests for API access from the frontend

# Initialize Talisman for HTTPS enforcement (optional, can be removed for local dev)
# For local development, Talisman can cause CSP issues - disable if needed
try:
    from flask_talisman import Talisman
    # Allow inline scripts and styles for development
    # In production, you should move scripts to external files and use nonces
    csp = {
        'default-src': "'self'",
        # Allow face-api and other trusted CDNs for model/script loading during development
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'font-src': "'self' data:",
        'connect-src': "'self' https://cdn.jsdelivr.net"
    }
    # Set TALISMAN_ENABLED=False in environment to disable
    if os.environ.get('TALISMAN_ENABLED', 'True').lower() != 'false':
        Talisman(app, force_https=False, content_security_policy=csp)
        print("Talisman enabled with CSP configured for inline scripts/styles")
    else:
        print("Talisman disabled for local development")
except ImportError:
    pass  # Talisman is optional

# Global error handlers - ensure all errors return JSON not HTML
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors with JSON response"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with JSON response"""
    print(f'Internal Server Error: {error}')
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors with JSON response"""
    return jsonify({'error': 'Bad request'}), 400

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(100))
    oauth_provider = db.Column(db.String(20))  # 'google', 'microsoft', or 'local'
    oauth_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        try:
            created_at = self.created_at.isoformat() if self.created_at else None
        except Exception:
            created_at = None
        
        try:
            profile_dict = self.profile.to_dict() if self.profile else None
        except Exception as e:
            print(f'Error converting profile to dict: {e}')
            profile_dict = None
        
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'oauth_provider': self.oauth_provider,
            'created_at': created_at,
            'profile': profile_dict
        }

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    language = db.Column(db.String(10), default='en')
    voice_speed = db.Column(db.Float, default=1.0)
    voice_pitch = db.Column(db.Float, default=1.0)
    voice_name = db.Column(db.String(50), default='default')
    messaging_platforms = db.Column(db.Text, default='[]')  # JSON array
    voice_pin = db.Column(db.String(255))  # Hashed voice PIN
    # Face encoding stored as JSON text (list of floats); may be absent in older DBs
    face_encoding = db.Column(db.Text)
    
    def to_dict(self):
        try:
            messaging_platforms = json.loads(self.messaging_platforms) if self.messaging_platforms else []
        except (json.JSONDecodeError, TypeError):
            messaging_platforms = []
        
        return {
            'language': self.language,
            'voice_speed': self.voice_speed,
            'voice_pitch': self.voice_pitch,
            'voice_name': self.voice_name,
            'messaging_platforms': messaging_platforms,
            'has_face': bool(getattr(self, 'face_encoding', None))
        }


class GmailToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    token_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def ensure_schema_migrations():
    """Apply lightweight schema adjustments without full migrations."""
    engine = db.engine
    inspector = inspect(engine)
    try:
        user_profile_cols = [col['name'] for col in inspector.get_columns('user_profile')]
        if 'face_encoding' not in user_profile_cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE user_profile ADD COLUMN face_encoding TEXT'))
                print('Added face_encoding column to user_profile')
    except Exception as exc:
        print(f'Schema migration skipped: {exc}')

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Main page - voice-driven interface"""
    return render_template('index.html')

@app.route('/api/auth/status')
def auth_status():
    """Check authentication status"""
    try:
        if 'user_id' in session:
            user_id = session.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user_dict = user.to_dict()
                    return jsonify({
                        'authenticated': True,
                        'user': user_dict
                    })
        return jsonify({'authenticated': False})
    except Exception as e:
        app.logger.exception('Error in auth_status: %s', str(e))
        # Still return a valid response even on error
        return jsonify({'authenticated': False, 'error': str(e)}), 200

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user with name, email, password and face capture"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')
        face_descriptors = data.get('face_descriptors')
        face_b64 = data.get('face_image')
        
        # Validate all required fields
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        if not face_descriptors:
            return jsonify({'error': 'Face capture is required for registration'}), 400
        
        if not face_b64:
            return jsonify({'error': 'Face image is required for registration'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            oauth_provider='local'
        )
        db.session.add(user)
        db.session.commit()
        
        # Create profile with face data
        profile = UserProfile(user_id=user.id)
        
        # Save face image
        try:
            header, encoded = face_b64.split(',', 1) if ',' in face_b64 else (None, face_b64)
            img_data = base64.b64decode(encoded)
            faces_dir = os.path.join(app.static_folder, 'faces')
            os.makedirs(faces_dir, exist_ok=True)
            img_path = os.path.join(faces_dir, f'{user.id}.jpg')
            with open(img_path, 'wb') as f:
                f.write(img_data)
            profile.face_image_path = f'faces/{user.id}.jpg'
        except Exception as e:
            print(f'Face image save error: {e}')
            db.session.delete(user)
            db.session.commit()
            return jsonify({'error': 'Failed to save face image'}), 400
        
        # Store face descriptors
        try:
            profile.face_encoding = json.dumps(face_descriptors)
        except Exception as e:
            print(f'Face descriptor save error: {e}')
            db.session.delete(user)
            db.session.commit()
            return jsonify({'error': 'Failed to save face data'}), 400
        
        db.session.add(profile)
        db.session.commit()
        
        print(f'User {email} registered with face verification')
        return jsonify({
            'success': True,
            'message': 'Registration successful with face verification',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        print(f'Registration endpoint error: {e}')
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': 'Registration failed: ' + str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with email/password; returns flag to trigger face verification"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Verify password
        if not check_password_hash(user.password_hash, password):
            print(f'Invalid password attempt for user {email}')
            return jsonify({'error': 'Invalid email or password'}), 401
        
        print(f'User {email} password verified - evaluating face verification requirement')
        
        disable_face = os.environ.get('DISABLE_FACE_VERIFICATION', 'false').lower() == 'true'
        has_face = bool(user.profile and getattr(user.profile, 'face_encoding', None))
        
        # Dev override: allow login without face verification
        if disable_face:
            session['user_id'] = user.id
            session['user_email'] = user.email
            return jsonify({
                'success': True,
                'message': 'Logged in (face verification disabled for development)'
            }), 200
        
        # Enforce face registration
        if not has_face:
            return jsonify({
                'error': 'Face registration required',
                'requires_face_setup': True,
                'email': email
            }), 400
        
        # Require face verification step
        return jsonify({
            'success': False,
            'requires_face_verification': True,
            'message': 'Please verify your face to complete login',
            'email': email
        }), 200
    
    except Exception as e:
        print(f'Login endpoint error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Login failed: ' + str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user by clearing the session"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/verify-face-login', methods=['POST'])
def verify_face_login():
    """Verify face during login after password has been checked"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        # Get user by email (password already verified in login endpoint)
        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has face registered
        if not user.profile or not user.profile.face_encoding:
            return jsonify({'error': 'No face registered for this user. Please complete face registration first.'}), 400
        
        # Get face descriptors from client
        incoming_descriptors = data.get('face_descriptors')
        if not incoming_descriptors:
            return jsonify({'error': 'No face descriptors provided'}), 400
        
        # Verify face by comparing descriptors
        try:
            stored_desc = json.loads(user.profile.face_encoding)
            
            # Compute Euclidean distance between descriptors
            if isinstance(incoming_descriptors, list) and len(incoming_descriptors) > 0:
                # Get first descriptor if multiple
                incoming_desc = incoming_descriptors[0] if isinstance(incoming_descriptors[0], list) else incoming_descriptors
            else:
                incoming_desc = incoming_descriptors
            
            distance = sum((a - b) ** 2 for a, b in zip(stored_desc, incoming_desc)) ** 0.5
            
            # face-api.js descriptors: distance < 0.6 is a good match
            if distance < 0.6:
                # Face verified - create session
                session['user_id'] = user.id
                print(f'User {email} logged in via face verification (distance: {distance:.4f})')
                return jsonify({'success': True, 'user': user.to_dict()})
            else:
                print(f'Face verification failed for {email} (distance: {distance:.4f})')
                return jsonify({'error': f'Face not recognized (distance: {distance:.4f}). Please try again.'}), 401
        except Exception as e:
            print(f'Face descriptor comparison error: {e}')
            return jsonify({'error': 'Face verification failed. Please try again.'}), 500
    
    except Exception as e:
        print(f'Face verification endpoint error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Face verification failed: ' + str(e)}), 500

@app.route('/api/auth/face-status', methods=['GET'])
def face_status():
    """Check if current user has face registered"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'authenticated': False, 'has_face': False}), 401
        
        user = User.query.get(user_id)
        if not user or not user.profile:
            return jsonify({'authenticated': True, 'has_face': False})
        
        has_face = bool(user.profile.face_encoding)
        return jsonify({
            'authenticated': True,
            'has_face': has_face,
            'email': user.email
        })
    except Exception as e:
        print(f'Face status check error: {e}')
        return jsonify({'error': 'Failed to check face status'}), 500

@app.route('/api/auth/oauth-pending-status', methods=['GET'])
def oauth_pending_status():
    """Check if there's a pending OAuth login waiting for face verification"""
    try:
        pending_user_id = session.get('pending_oauth_user_id')
        if not pending_user_id:
            return jsonify({'pending': False})
        
        user = User.query.get(pending_user_id)
        if not user:
            return jsonify({'pending': False})
        
        requires_registration = session.get('oauth_requires_face_registration', False)
        requires_verification = session.get('oauth_requires_face_verification', False)
        
        return jsonify({
            'pending': True,
            'user': {
                'email': user.email,
                'name': user.name
            },
            'requires_face_registration': requires_registration,
            'requires_face_verification': requires_verification
        })
    except Exception as e:
        print(f'OAuth pending status error: {e}')
        return jsonify({'error': 'Failed to check OAuth status'}), 500

@app.route('/api/auth/complete-oauth-face-registration', methods=['POST'])
def complete_oauth_face_registration():
    """Complete OAuth login by registering face for new OAuth users"""
    try:
        pending_user_id = session.get('pending_oauth_user_id')
        if not pending_user_id:
            return jsonify({'error': 'No pending OAuth login'}), 400
        
        user = User.query.get(pending_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        face_descriptors = data.get('face_descriptors')
        face_b64 = data.get('face_image')
        
        if not face_descriptors or not face_b64:
            return jsonify({'error': 'Face capture is required'}), 400
        
        # Save face image
        try:
            header, encoded = face_b64.split(',', 1) if ',' in face_b64 else (None, face_b64)
            img_data = base64.b64decode(encoded)
            faces_dir = os.path.join(app.static_folder, 'faces')
            os.makedirs(faces_dir, exist_ok=True)
            img_path = os.path.join(faces_dir, f'{user.id}.jpg')
            with open(img_path, 'wb') as f:
                f.write(img_data)
            user.profile.face_image_path = f'faces/{user.id}.jpg'
        except Exception as e:
            print(f'Face image save error: {e}')
            return jsonify({'error': 'Failed to save face image'}), 400
        
        # Store face descriptors
        try:
            user.profile.face_encoding = json.dumps(face_descriptors)
        except Exception as e:
            print(f'Face descriptor save error: {e}')
            return jsonify({'error': 'Failed to save face data'}), 400
        
        db.session.commit()
        
        # Complete login
        session['user_id'] = user.id
        session.pop('pending_oauth_user_id', None)
        session.pop('oauth_requires_face_registration', None)
        
        print(f'OAuth user {user.email} completed face registration and logged in')
        return jsonify({
            'success': True,
            'message': 'Face registered successfully',
            'user': user.to_dict()
        })
    
    except Exception as e:
        print(f'OAuth face registration error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Face registration failed: ' + str(e)}), 500

@app.route('/api/auth/complete-oauth-face-verification', methods=['POST'])
def complete_oauth_face_verification():
    """Complete OAuth login by verifying face for returning OAuth users"""
    try:
        pending_user_id = session.get('pending_oauth_user_id')
        if not pending_user_id:
            return jsonify({'error': 'No pending OAuth login'}), 400
        
        user = User.query.get(pending_user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.profile or not user.profile.face_encoding:
            return jsonify({'error': 'No face registered for this user'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        incoming_descriptors = data.get('face_descriptors')
        if not incoming_descriptors:
            return jsonify({'error': 'No face descriptors provided'}), 400
        
        # Verify face by comparing descriptors
        try:
            stored_desc = json.loads(user.profile.face_encoding)
            
            # Compute Euclidean distance between descriptors
            if isinstance(incoming_descriptors, list) and len(incoming_descriptors) > 0:
                incoming_desc = incoming_descriptors[0] if isinstance(incoming_descriptors[0], list) else incoming_descriptors
            else:
                incoming_desc = incoming_descriptors
            
            distance = sum((a - b) ** 2 for a, b in zip(stored_desc, incoming_desc)) ** 0.5
            
            # face-api.js descriptors: distance < 0.6 is a good match
            if distance < 0.6:
                # Face verified - complete login
                session['user_id'] = user.id
                session.pop('pending_oauth_user_id', None)
                session.pop('oauth_requires_face_verification', None)
                
                print(f'OAuth user {user.email} verified face and logged in (distance: {distance:.4f})')
                return jsonify({
                    'success': True,
                    'message': 'Face verified successfully',
                    'user': user.to_dict()
                })
            else:
                print(f'OAuth face verification failed for {user.email} (distance: {distance:.4f})')
                return jsonify({'error': f'Face not recognized (distance: {distance:.4f}). Please try again.'}), 401
        except Exception as e:
            print(f'Face descriptor comparison error: {e}')
            return jsonify({'error': 'Face verification failed. Please try again.'}), 500
    
    except Exception as e:
        print(f'OAuth face verification error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Face verification failed: ' + str(e)}), 500

@app.route('/api/auth/face-login', methods=['POST'])
def face_login():
    """Login using only face recognition - no email or password required"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Request body is empty'}), 400
        
        # Get face descriptors from client
        incoming_descriptors = data.get('face_descriptors')
        if not incoming_descriptors:
            return jsonify({'error': 'No face descriptors provided'}), 400
        
        # Query all users with face encoding
        users = User.query.join(UserProfile).filter(UserProfile.face_encoding.isnot(None)).all()
        
        if not users:
            return jsonify({'error': 'No registered users with face data found'}), 404
        
        # Try to match face against all registered users
        best_match = None
        best_distance = float('inf')
        
        for user in users:
            if not user.profile or not user.profile.face_encoding:
                continue
            
            try:
                stored_desc = json.loads(user.profile.face_encoding)
                
                # Compute Euclidean distance between descriptors
                if isinstance(incoming_descriptors, list) and len(incoming_descriptors) > 0:
                    # Get first descriptor if multiple
                    incoming_desc = incoming_descriptors[0] if isinstance(incoming_descriptors[0], list) else incoming_descriptors
                else:
                    incoming_desc = incoming_descriptors
                
                distance = sum((a - b) ** 2 for a, b in zip(stored_desc, incoming_desc)) ** 0.5
                
                # Track best match
                if distance < best_distance:
                    best_distance = distance
                    best_match = user
                    
            except Exception as e:
                print(f'Error comparing face for user {user.email}: {e}')
                continue
        
        # face-api.js descriptors: distance < 0.6 is a good match
        if best_match and best_distance < 0.6:
            # Face matched - create session
            session['user_id'] = best_match.id
            print(f'User {best_match.email} logged in via face-only authentication (distance: {best_distance:.4f})')
            return jsonify({
                'success': True,
                'user': best_match.to_dict(),
                'message': f'Welcome back, {best_match.name}!',
                'match_confidence': round((1 - best_distance) * 100, 2)
            })
        else:
            if best_match:
                print(f'Best face match was {best_match.email} with distance {best_distance:.4f}, but threshold not met')
            else:
                print('No face matches found')
            return jsonify({
                'error': 'Face not recognized. Please try again or use email/password login.',
                'best_distance': best_distance if best_match else None
            }), 401
    
    except Exception as e:
        print(f'Face-only login endpoint error: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Face login failed: ' + str(e)}), 500

@app.route('/auth/google')
def google_auth():
    """Initiate Google OAuth"""
    if not app.config['GOOGLE_CLIENT_ID']:
        return jsonify({'error': 'Google OAuth not configured'}), 500
    
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': app.config['GOOGLE_CLIENT_ID'],
                'client_secret': app.config['GOOGLE_CLIENT_SECRET'],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    # Disable scope change warnings - Google may return additional scopes
    flow.oauth2session._client.scope = None
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if 'error' in request.args:
        print(f'OAuth error from Google: {request.args.get("error")}')
        return redirect(url_for('index', error=request.args.get('error')))
    
    try:
        # Get the state from session
        stored_state = session.get('oauth_state')
        if not stored_state:
            print('No OAuth state found in session')
            return redirect(url_for('index', error='oauth_state_missing'))
        
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': app.config['GOOGLE_CLIENT_ID'],
                    'client_secret': app.config['GOOGLE_CLIENT_SECRET'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI,
            state=stored_state
        )
        
        # Disable scope change warnings - Google may return additional scopes
        flow.oauth2session._client.scope = None
        
        # Build the authorization response URL properly
        # Use the scheme from GOOGLE_REDIRECT_URI to ensure consistency
        authorization_response = request.url

        # If our registered redirect is http but the browser came back over https,
        # normalize to avoid redirect_uri_mismatch during local dev with proxies.
        if GOOGLE_REDIRECT_URI.startswith('http://') and authorization_response.startswith('https://'):
            authorization_response = authorization_response.replace('https://', 'http://', 1)
            print('Adjusted authorization_response scheme from https to http to match GOOGLE_REDIRECT_URI')
        
        print(f'Authorization response URL: {authorization_response}')
        print(f'Expected redirect URI: {GOOGLE_REDIRECT_URI}')
        
        # Fetch token - ignore scope change warnings from oauthlib
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*Scope has changed.*')
            try:
                flow.fetch_token(authorization_response=authorization_response)
            except Warning as w:
                if "Scope has changed" in str(w):
                    logger.info(f'Ignoring scope change warning from Google OAuth: {w}')
                    # OAuthlib raises Warning as an exception after parsing the token.
                    # Credentials are already populated on the flow, so we can proceed.
                else:
                    raise
        
        credentials = flow.credentials
        print(f'OAuth token fetched successfully')
    except Exception as e:
        print(f'OAuth token fetch error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        from urllib.parse import quote
        msg = quote(str(e)[:200]) if str(e) else 'oauth_failed'
        return redirect(url_for('index') + f'?error=oauth_failed&msg={msg}')
    
    # Get user info
    user_info = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {credentials.token}'}
    ).json()
    
    # Create or update user
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(
            email=user_info['email'],
            name=user_info.get('name', ''),
            oauth_provider='google',
            oauth_id=user_info['id']
        )
        db.session.add(user)
        db.session.commit()
        
        # Create default profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    else:
        if not user.oauth_provider:
            user.oauth_provider = 'google'
            user.oauth_id = user_info['id']
            db.session.commit()
    
    # Check if user has face registered
    has_face = bool(user.profile and user.profile.face_encoding)
    
    if not has_face:
        # Store user info in session but don't log them in yet
        session['pending_oauth_user_id'] = user.id
        session['oauth_requires_face_registration'] = True
        print(f'Google OAuth user {user.email} needs face registration')
        return redirect(url_for('index', oauth='google', face_registration_required='true'))
    else:
        # User has face registered - require face verification before login
        session['pending_oauth_user_id'] = user.id
        session['oauth_requires_face_verification'] = True
        print(f'Google OAuth user {user.email} requires face verification')
        return redirect(url_for('index', oauth='google', face_verification_required='true'))

@app.route('/api/profile', methods=['GET', 'PUT'])
def profile():
    """Get or update user profile and preferences"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if request.method == 'GET':
        if not user.profile:
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
        return jsonify(user.profile.to_dict())
    
    # PUT - Update profile
    data = request.json
    if not user.profile:
        user.profile = UserProfile(user_id=user.id)
    
    if 'language' in data:
        user.profile.language = data['language']
    if 'voice_speed' in data:
        user.profile.voice_speed = float(data['voice_speed'])
    if 'voice_pitch' in data:
        user.profile.voice_pitch = float(data['voice_pitch'])
    if 'voice_name' in data:
        user.profile.voice_name = data['voice_name']
    if 'messaging_platforms' in data:
        user.profile.messaging_platforms = json.dumps(data['messaging_platforms'])
    if 'preferences' in data:
        user.profile.preferences = json.dumps(data['preferences'])
    if 'voice_pin' in data:
        user.profile.voice_pin = generate_password_hash(data['voice_pin'])
    
    db.session.commit()
    return jsonify({'success': True, 'profile': user.profile.to_dict()})

@app.route('/api/voice/process', methods=['POST'])
def process_voice():
    """Process voice command text and return intent"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    from command_processor import get_command_processor
    
    processor = get_command_processor()
    result = processor.process_command(text)
    
    # Add response message based on intent
    responses = {
        'help': 'I can help you with reading emails, sending messages, and more. Just say what you need!',
        'unknown': 'I did not understand that command. Say "help" for available commands.'
    }
    
    response_text = responses.get(result.intent.value, 'Command processed.')
    
    return jsonify({
        'success': True,
        'intent': result.intent.value,
        'confidence': result.confidence,
        'entities': result.entities,
        'action': result.action,
        'response': response_text
    })

@app.route('/api/voice/recognize', methods=['POST'])
def recognize_voice():
    """Server-side voice recognition (fallback)"""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
        
        # Try Google Speech Recognition first
        try:
            text = recognizer.recognize_google(audio)
            return jsonify({'text': text})
        except sr.UnknownValueError:
            return jsonify({'error': 'Could not understand audio'}), 400
        except sr.RequestError:
            # Fallback to offline recognition if available
            return jsonify({'error': 'Speech recognition service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Face Recognition Helper Functions
# ---------------------------------------------------------------------------

@app.route('/api/face/verify', methods=['POST'])
def verify_face_endpoint():
    """Verify face during login using client-side computed descriptors"""
    data = request.json
    email = data.get('email')
    face_descriptors = data.get('face_descriptors')
    
    if not email or not face_descriptors:
        return jsonify({'error': 'Email and face descriptors required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not user.profile or not user.profile.face_encoding:
        return jsonify({'error': 'No face registered for this user'}), 400
    
    try:
        # Compare face descriptors using Euclidean distance
        stored_desc = json.loads(user.profile.face_encoding)
        incoming_desc = face_descriptors
        
        # Compute Euclidean distance between descriptors
        distance = sum((a - b) ** 2 for a, b in zip(stored_desc, incoming_desc)) ** 0.5
        
        # face-api.js descriptors: distance < 0.6 is a good match
        if distance < 0.6:
            session['user_id'] = user.id
            print(f'User {email} verified via face recognition (distance: {distance:.4f})')
            return jsonify({'success': True, 'user': user.to_dict()})
        else:
            print(f'Face verification failed for {email} (distance: {distance:.4f})')
            return jsonify({'error': f'Face not recognized. Please try again or use password.'}), 401
    except Exception as e:
        print(f'Face verification error: {e}')
        return jsonify({'error': 'Face verification failed'}), 500

@app.route('/api/voice-pin/setup', methods=['POST'])
def setup_voice_pin():
    """Setup voice PIN for enhanced security"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.json
        voice_pin = data.get('voice_pin')
        
        if not voice_pin or len(str(voice_pin)) < 4:
            return jsonify({'error': 'Voice PIN must be at least 4 digits'}), 400
        
        if not user.profile:
            user.profile = UserProfile(user_id=user.id)
        
        # Hash the voice PIN
        user.profile.voice_pin = generate_password_hash(str(voice_pin))
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Voice PIN setup successfully',
            'has_voice_pin': True
        })
    
    except Exception as e:
        print(f'Voice PIN setup error: {e}')
        db.session.rollback()
        return jsonify({'error': 'Failed to setup voice PIN'}), 500

@app.route('/api/voice-pin/verify', methods=['POST'])
def verify_voice_pin():
    """Verify voice PIN for authentication"""
    try:
        data = request.json
        email = data.get('email')
        voice_pin = data.get('voice_pin')
        
        if not email or not voice_pin:
            return jsonify({'error': 'Email and voice PIN required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.profile or not user.profile.voice_pin:
            return jsonify({'error': 'No voice PIN registered for this user'}), 400
        
        # Verify the voice PIN
        if check_password_hash(user.profile.voice_pin, str(voice_pin)):
            session['user_id'] = user.id
            print(f'User {email} verified via voice PIN')
            return jsonify({'success': True, 'user': user.to_dict()})
        else:
            print(f'Invalid voice PIN attempt for user {email}')
            return jsonify({'error': 'Invalid voice PIN'}), 401
    
    except Exception as e:
        print(f'Voice PIN verification error: {e}')
        return jsonify({'error': 'Voice PIN verification failed'}), 500

@app.route('/api/voice-pin/check', methods=['GET'])
def check_voice_pin():
    """Check if user has voice PIN registered"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'authenticated': False, 'has_voice_pin': False}), 401
        
        user = User.query.get(user_id)
        if not user or not user.profile:
            return jsonify({'authenticated': True, 'has_voice_pin': False})
        
        has_voice_pin = bool(user.profile.voice_pin)
        return jsonify({
            'authenticated': True,
            'has_voice_pin': has_voice_pin,
            'email': user.email
        })
    except Exception as e:
        print(f'Voice PIN check error: {e}')
        return jsonify({'error': 'Failed to check voice PIN status'}), 500

# ---------------------------------------------------------------------------
# MILESTONE 2: Gmail API & Voice Commands
# ---------------------------------------------------------------------------

@app.route('/api/gmail/auth', methods=['GET'])
def gmail_auth():
    """Initiate Gmail OAuth flow"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        from gmail_service import create_gmail_oauth_flow
        
        redirect_uri = os.environ.get('GMAIL_REDIRECT_URI', 'http://localhost:5000/api/gmail/callback')
        flow = create_gmail_oauth_flow(redirect_uri)
        
        # Note: scope flexibility is already set in create_gmail_oauth_flow()
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        session['gmail_oauth_state'] = state
        
        return jsonify({
            'authorization_url': authorization_url,
            'state': state
        })
        
    except Exception as e:
        logger.error(f'Gmail auth error: {e}')
        return jsonify({'error': 'Failed to initiate Gmail authentication'}), 500

@app.route('/api/gmail/callback', methods=['GET'])
def gmail_callback():
    """Handle Gmail OAuth callback"""
    try:
        # Log incoming args and session state for debugging
        logger.info(f"Gmail callback query: {dict(request.args)}")
        logger.info(f"Session keys: {list(session.keys())}")

        # Check if Google returned an error
        error = request.args.get('error')
        if error:
            logger.error(f'OAuth error from Google: {error}')
            error_description = request.args.get('error_description', error)
            return redirect(url_for('index') + f'?error=oauth_{error}&msg={error_description}')

        user_id = session.get('user_id')
        if not user_id:
            logger.error('No user_id in session during callback')
            return redirect(url_for('index') + '?error=not_authenticated&msg=session_missing_user')

        session_state = session.get('gmail_oauth_state')
        state_param = request.args.get('state')
        if not session_state:
            logger.error('No gmail_oauth_state in session')
            return redirect(url_for('index') + '?error=invalid_state&msg=session_state_missing')
        if not state_param:
            logger.error('No state parameter returned from Google')
            return redirect(url_for('index') + '?error=invalid_state&msg=state_param_missing')
        if session_state != state_param:
            logger.error(f'State mismatch. Session state: {session_state}, returned: {state_param}')
            return redirect(url_for('index') + '?error=invalid_state&msg=state_mismatch')

        from gmail_service import create_gmail_oauth_flow

        redirect_uri = os.environ.get('GMAIL_REDIRECT_URI', 'http://localhost:5000/api/gmail/callback')
        flow = create_gmail_oauth_flow(redirect_uri)

        # Note: scope flexibility is already set in create_gmail_oauth_flow()
        
        # Normalize the callback URL scheme to match the registered redirect URI.
        authorization_response = request.url
        if redirect_uri.startswith('http://') and authorization_response.startswith('https://'):
            # During local dev behind proxies Chrome can hit https while our OAuth client expects http
            authorization_response = authorization_response.replace('https://', 'http://', 1)
            logger.info('Adjusted authorization_response scheme from https to http to match redirect_uri')

        logger.info(f'Fetching token with callback URL: {authorization_response}')
        
        # Fetch token - ignore scope change warnings from oauthlib
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='.*Scope has changed.*')
            try:
                flow.fetch_token(authorization_response=authorization_response)
            except Warning as w:
                if "Scope has changed" in str(w):
                    logger.info(f'Ignoring scope change warning from Gmail OAuth: {w}')
                    # OAuthlib raises Warning as an exception after parsing the token.
                    # Credentials are already populated on the flow, so we can proceed.
                else:
                    raise

        credentials = flow.credentials

        # Store credentials in session (in production, store securely in database)
        token_payload = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        session['gmail_token'] = token_payload

        # Persist token per user so they stay connected across logins
        try:
            token_record = GmailToken.query.filter_by(user_id=user_id).first()
            if not token_record:
                token_record = GmailToken(user_id=user_id, token_json=json.dumps(token_payload))
                db.session.add(token_record)
            else:
                token_record.token_json = json.dumps(token_payload)
            db.session.commit()
        except Exception as db_err:
            logger.error(f'Failed to persist Gmail token: {db_err}')

        print(f"[GMAIL CALLBACK] Authentication successful")
        return redirect(url_for('index') + '?gmail_auth=success')

    except Exception as e:
        error_str = str(e)
        print(f"[GMAIL CALLBACK] Exception occurred: {type(e).__name__}: {error_str}")
        import traceback
        traceback.print_exc()
        
        # URL encode the error message properly
        from urllib.parse import quote
        msg = quote(error_str[:100]) if error_str else 'unknown_error'
        return redirect(url_for('index') + f'?error=oauth_failed&msg={msg}')

@app.route('/api/gmail/status', methods=['GET'])
def gmail_status():
    """Check Gmail authentication status"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'authenticated': False}), 401
        
        # Check test mode
        test_mode = os.environ.get('GMAIL_TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            return jsonify({
                'authenticated': True,
                'gmail_connected': True,
                'test_mode': True
            })
        
        gmail_token = session.get('gmail_token')

        # If session does not have Gmail token, attempt to load from DB
        if not gmail_token:
            token_record = GmailToken.query.filter_by(user_id=user_id).first()
            if token_record:
                try:
                    gmail_token = json.loads(token_record.token_json)
                    session['gmail_token'] = gmail_token
                except Exception:
                    gmail_token = None
        
        if gmail_token:
            return jsonify({
                'authenticated': True,
                'gmail_connected': True
            })
        else:
            return jsonify({
                'authenticated': True,
                'gmail_connected': False
            })
            
    except Exception as e:
        logger.error(f'Gmail status error: {e}')
        return jsonify({'error': 'Failed to check Gmail status'}), 500

@app.route('/api/gmail/messages', methods=['GET'])
def get_gmail_messages():
    """Get Gmail messages"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Check test mode
        test_mode = os.environ.get('GMAIL_TEST_MODE', 'false').lower() == 'true'
        if test_mode:
            # Return mock emails for testing
            mock_emails = [
                {
                    'id': 'test_1',
                    'from': 'john@example.com',
                    'to': os.environ.get('GMAIL_TEST_EMAIL', 'you@gmail.com'),
                    'subject': 'Welcome to Gmail Test Mode',
                    'snippet': 'This is a test email to demonstrate Gmail functionality...',
                    'body': 'This is a test email to demonstrate Gmail functionality. You can read, reply, and delete emails using voice commands.',
                    'date': '2026-01-19T10:30:00',
                    'is_unread': True
                },
                {
                    'id': 'test_2',
                    'from': 'sarah@example.com',
                    'to': os.environ.get('GMAIL_TEST_EMAIL', 'you@gmail.com'),
                    'subject': 'Project Update',
                    'snippet': 'Here is the latest project status...',
                    'body': 'Here is the latest project status. Everything is on track for delivery next week.',
                    'date': '2026-01-18T14:15:00',
                    'is_unread': False
                },
                {
                    'id': 'test_3',
                    'from': 'manager@example.com',
                    'to': os.environ.get('GMAIL_TEST_EMAIL', 'you@gmail.com'),
                    'subject': 'Meeting Reminder',
                    'snippet': 'Don\'t forget about tomorrow\'s team meeting at 2 PM...',
                    'body': 'Don\'t forget about tomorrow\'s team meeting at 2 PM in the main conference room.',
                    'date': '2026-01-17T09:00:00',
                    'is_unread': False
                }
            ]
            return jsonify({
                'success': True,
                'messages': mock_emails,
                'count': len(mock_emails),
                'test_mode': True
            })
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            token_record = GmailToken.query.filter_by(user_id=user_id).first()
            if token_record:
                try:
                    gmail_token = json.loads(token_record.token_json)
                    session['gmail_token'] = gmail_token
                except Exception:
                    gmail_token = None
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        # Get query parameters
        max_results = int(request.args.get('max_results', 25))
        query = request.args.get('query', '')
        
        # Log what we're fetching (helps troubleshoot folder queries)
        if 'in:trash' in query:
            logger.info(f"Fetching trash emails with query: {query}")
        elif 'in:sent' in query:
            logger.info(f"Fetching sent emails with query: {query}")
        elif query:
            logger.info(f"Fetching emails with query: {query}")
        else:
            logger.info(f"Fetching inbox emails")
        
        # Pass query directly to gmail service - it will use Gmail search syntax
        messages = gmail.get_messages(max_results=max_results, query=query, label_ids=None)
        logger.info(f"Got {len(messages)} messages with query='{query}'")
        
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        logger.error(f'Get messages error: {e}')
        return jsonify({'error': 'Failed to get messages'}), 500

@app.route('/api/gmail/message/<message_id>', methods=['GET'])
def get_gmail_message(message_id):
    """Get single Gmail message"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        message = gmail.get_message(message_id)
        
        if message:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({'error': 'Message not found'}), 404
            
    except Exception as e:
        logger.error(f'Get message error: {e}')
        return jsonify({'error': 'Failed to get message'}), 500

@app.route('/api/gmail/send', methods=['POST'])
def send_gmail():
    """Send Gmail message"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not to or not subject or not body:
            return jsonify({'error': 'Missing required fields'}), 400
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        result = gmail.send_message(
            to=to,
            subject=subject,
            body=body,
            cc=data.get('cc'),
            bcc=data.get('bcc')
        )
        
        if result:
            return jsonify({
                'success': True,
                'message_id': result['id']
            })
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        logger.error(f'Send email error: {e}')
        return jsonify({'error': 'Failed to send email'}), 500

@app.route('/api/gmail/reply/<message_id>', methods=['POST'])
def reply_gmail(message_id):
    """Reply to Gmail message"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        data = request.json
        body = data.get('body')
        
        if not body:
            return jsonify({'error': 'Reply body required'}), 400
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        result = gmail.reply_to_message(message_id, body)
        
        if result:
            return jsonify({
                'success': True,
                'message_id': result['id']
            })
        else:
            return jsonify({'error': 'Failed to send reply'}), 500
            
    except Exception as e:
        logger.error(f'Reply error: {e}')
        return jsonify({'error': 'Failed to send reply'}), 500

@app.route('/api/gmail/labels', methods=['GET'])
def get_gmail_labels():
    """Get available Gmail labels (for debugging)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        # Get all labels
        results = gmail.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        logger.info(f"Available labels: {[{'name': l['name'], 'id': l['id']} for l in labels]}")
        
        return jsonify({
            'success': True,
            'labels': [{'name': l['name'], 'id': l['id']} for l in labels]
        })
    except Exception as e:
        logger.error(f'Get labels error: {e}')
        return jsonify({'error': f'Failed to get labels: {str(e)}'}), 500

@app.route('/api/gmail/delete/<message_id>', methods=['DELETE'])
def delete_gmail(message_id):
    """Delete Gmail message"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        success = gmail.delete_message(message_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete message'}), 500
            
    except Exception as e:
        logger.error(f'Delete error: {e}')
        return jsonify({'error': 'Failed to delete message'}), 500

@app.route('/api/gmail/search', methods=['GET'])
def search_gmail():
    """Search Gmail messages"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        if not gmail_token:
            return jsonify({'error': 'Gmail not connected'}), 401
        
        query = request.args.get('query', '')
        max_results = int(request.args.get('max_results', 25))
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        from gmail_service import GmailService
        
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        
        messages = gmail.search_messages(query, max_results)
        
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        })
        
    except Exception as e:
        logger.error(f'Search error: {e}')
        return jsonify({'error': 'Failed to search messages'}), 500

@app.route('/api/voice/process-command', methods=['POST'])
def process_voice_command():
    """Process voice command using NLU"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.json
        command_text = data.get('command')
        
        if not command_text:
            return jsonify({'error': 'Command text required'}), 400
        
        from command_processor import get_command_processor
        
        processor = get_command_processor()
        result = processor.process_command(command_text)
        
        return jsonify({
            'success': True,
            'result': result.to_dict()
        })
        
    except Exception as e:
        logger.error(f'Command processing error: {e}')
        return jsonify({'error': 'Failed to process command'}), 500

@app.route('/api/voice/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio to text using Whisper/Vosk"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        language = request.form.get('language', 'en')
        
        from speech_recognition_service import get_speech_service
        
        speech_service = get_speech_service()
        
        # Read audio data
        audio_data = audio_file.read()
        
        # Transcribe
        result = speech_service.transcribe_audio_data(audio_data, language=language)
        
        return jsonify({
            'success': result['success'],
            'text': result.get('text', ''),
            'engine': result.get('engine'),
            'confidence': result.get('confidence')
        })
        
    except Exception as e:
        logger.error(f'Transcription error: {e}')
        return jsonify({'error': 'Failed to transcribe audio'}), 500

@app.route('/api/tts/speak', methods=['POST'])
def speak_text():
    """Convert text to speech"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.json
        text = data.get('text')
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        from tts_service import get_tts_service
        
        tts = get_tts_service()
        success = tts.speak(text, async_mode=True)
        
        return jsonify({
            'success': success
        })
        
    except Exception as e:
        logger.error(f'TTS error: {e}')
        return jsonify({'error': 'Failed to speak text'}), 500

@app.route('/api/tts/read-email/<message_id>', methods=['POST'])
def read_email_aloud(message_id):
    """Read email aloud using TTS"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            logger.error('Read email: user not authenticated')
            return jsonify({'error': 'Not authenticated'}), 401
        
        gmail_token = session.get('gmail_token')
        
        # If session does not have Gmail token, attempt to load from DB
        if not gmail_token:
            token_record = GmailToken.query.filter_by(user_id=user_id).first()
            if token_record:
                try:
                    gmail_token = json.loads(token_record.token_json)
                    session['gmail_token'] = gmail_token
                    logger.info('Loaded Gmail token from DB for read-email')
                except Exception as db_err:
                    logger.error(f'Failed to load Gmail token from DB: {db_err}')
                    gmail_token = None
        
        if not gmail_token:
            logger.error('Read email: Gmail not connected')
            return jsonify({'error': 'Gmail not connected'}), 401
        
        from gmail_service import GmailService
        from tts_service import get_tts_service
        
        # Get email
        logger.info(f'Reading email {message_id} aloud')
        gmail = GmailService()
        gmail.authenticate(gmail_token)
        message = gmail.get_message(message_id)
        
        if not message:
            logger.error(f'Message {message_id} not found')
            return jsonify({'error': 'Message not found'}), 404
        
        # Read email aloud
        tts = get_tts_service()
        success = tts.read_email(message, include_body=True)
        
        if not success:
            logger.warning(f'TTS read_email returned False for message {message_id}')
            return jsonify({
                'success': False,
                'error': 'Failed to generate speech for email'
            }), 400
        
        return jsonify({
            'success': success
        })
        
    except Exception as e:
        logger.error(f'Read email error: {e}', exc_info=True)
        return jsonify({'error': 'Failed to read email', 'details': str(e)}), 500

# ---------------------------------------------------------------------------
# Admin & Utility Routes
# ---------------------------------------------------------------------------

@app.route('/api/admin/reset-db', methods=['POST'])
def reset_database():
    """Reset database - useful for fixing schema issues. Only for development."""
    if app.config.get('ENV') == 'production':
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        db.drop_all()
        db.create_all()
        ensure_schema_migrations()
        return jsonify({'success': True, 'message': 'Database reset successfully'})
    except Exception as e:
        print(f'Database reset error: {e}')
        return jsonify({'error': 'Database reset failed'}), 500

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            ensure_schema_migrations()
        except Exception as e:
            print(f'Error creating database: {e}')
            print('Attempting to reset database...')
            try:
                db.drop_all()
                db.create_all()
                ensure_schema_migrations()
                print('Database reset successfully')
            except Exception as reset_error:
                print(f'Failed to reset database: {reset_error}')
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

