"""
Voice-Based Email & Messaging Assistant
Milestone 1: Authentication & Profile Management with Voice Commands
"""
import os
# Allow OAuth over HTTP during local development (never enable in production).
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
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
import io
from PIL import Image

# Load environment variables
load_dotenv()

# Debug: Print loaded credentials (remove in production)
print("=" * 60)
print("ENVIRONMENT VARIABLES LOADED:")
print(f"  GOOGLE_CLIENT_ID: {'✓ LOADED' if os.environ.get('GOOGLE_CLIENT_ID') else '✗ NOT FOUND'}")
print(f"  GOOGLE_CLIENT_SECRET: {'✓ LOADED' if os.environ.get('GOOGLE_CLIENT_SECRET') else '✗ NOT FOUND'}")
print(f"  GOOGLE_REDIRECT_URI: {os.environ.get('GOOGLE_REDIRECT_URI', 'NOT FOUND')}")
print("=" * 60)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///voice_assistant.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

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
    # Face auth fields
    face_image_path = db.Column(db.String(255))
    face_encoding = db.Column(db.Text)  # JSON list of floats
    preferences = db.Column(db.Text, default='{}')  # JSON object
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        try:
            face_path = self.face_image_path
            face_enc = self.face_encoding
        except Exception:
            # Columns may not exist in old database schema
            face_path = None
            face_enc = None
        
        try:
            messaging_platforms = json.loads(self.messaging_platforms) if self.messaging_platforms else []
        except (json.JSONDecodeError, TypeError):
            messaging_platforms = []
        
        try:
            preferences = json.loads(self.preferences) if self.preferences else {}
        except (json.JSONDecodeError, TypeError):
            preferences = {}
        
        return {
            'language': self.language,
            'voice_speed': self.voice_speed,
            'voice_pitch': self.voice_pitch,
            'voice_name': self.voice_name,
            'messaging_platforms': messaging_platforms,
            'preferences': preferences,
            'face_image_path': face_path,
            'has_face': bool(face_enc)
        }

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
        return jsonify({'error': 'Registration failed: ' + str(e)}), 500
        
        session['user_id'] = user.id
        return jsonify({'success': True, 'user': user.to_dict()})
    
    except Exception as e:
        print(f'Register endpoint error: {e}')
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
        
        print(f'User {email} password verified - face verification required')
        
        # Check if user has face registered
        has_face = bool(user.profile and user.profile.face_encoding)
        
        if not has_face:
            return jsonify({
                'error': 'Face registration required',
                'requires_face_setup': True,
                'email': email
            }), 400
        
        # Return flag indicating face verification is needed
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
        
        # Build the authorization response URL properly
        # Use the scheme from GOOGLE_REDIRECT_URI to ensure consistency
        authorization_response = request.url
        
        # Ensure HTTP for localhost if that's what we configured
        if 'localhost' in GOOGLE_REDIRECT_URI or '127.0.0.1' in GOOGLE_REDIRECT_URI:
            if GOOGLE_REDIRECT_URI.startswith('http://'):
                authorization_response = authorization_response.replace('https://', 'http://', 1)
        
        print(f'Authorization response URL: {authorization_response}')
        print(f'Expected redirect URI: {GOOGLE_REDIRECT_URI}')
        
        flow.fetch_token(authorization_response=authorization_response)
        credentials = flow.credentials
        print(f'OAuth token fetched successfully')
    except Exception as e:
        print(f'OAuth token fetch error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index', error='oauth_failed'))
    
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
    
    processor = VoiceCommandProcessor()
    result = processor.process_command(text)
    if result['action'] == 'login_google':
        result['response'] = 'Redirecting you to Google login.'
        result['redirect'] = '/auth/google'
        return jsonify(result)

    # Add response message based on action
    responses = {
        'greeting': 'Hello! How can I help you today?',
        'login': 'Please say your email address to login.',
        'register': 'Please say your email address to register.',
        'profile': 'Opening your profile settings.',
        'logout': 'Logging you out. Goodbye!',
        'help': 'I can help you with login, register, profile, and logout. Just say what you need!',
        'test': 'Voice recognition is working perfectly!',
        'unknown': 'I did not understand that command. Say "help" for available commands.'
    }
    
    result['response'] = responses.get(result['action'], 'Command processed.')
    return jsonify(result)

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
def save_face_image(base64_data, user_id):
    """Save base64 face image and return the path"""
    try:
        # Decode base64 image
        if ',' in base64_data:
            header, encoded = base64_data.split(',', 1)
        else:
            encoded = base64_data
        
        img_data = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(img_data))
        
        # Save to static/faces directory
        faces_dir = os.path.join(app.static_folder, 'faces')
        os.makedirs(faces_dir, exist_ok=True)
        
        img_path = os.path.join(faces_dir, f'{user_id}.jpg')
        img.save(img_path, 'JPEG')
        
        return img_path
    except Exception as e:
        print(f"Error saving face image: {e}")
        return None


def verify_face(stored_encoding, incoming_encoding, tolerance=0.6):
    """Verify if two face encodings match using Euclidean distance"""
    try:
        if not stored_encoding or not incoming_encoding:
            return False

        # Compute Euclidean distance
        distance = sum((a - b) ** 2 for a, b in zip(stored_encoding, incoming_encoding)) ** 0.5
        return distance < tolerance
    except Exception as e:
        print(f"Error verifying face: {e}")
        return False

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

@app.route('/api/admin/reset-db', methods=['POST'])
def reset_database():
    """Reset database - useful for fixing schema issues. Only for development."""
    if app.config.get('ENV') == 'production':
        return jsonify({'error': 'Not available in production'}), 403
    
    try:
        db.drop_all()
        db.create_all()
        return jsonify({'success': True, 'message': 'Database reset successfully'})
    except Exception as e:
        print(f'Database reset error: {e}')
        return jsonify({'error': 'Database reset failed'}), 500

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f'Error creating database: {e}')
            print('Attempting to reset database...')
            try:
                db.drop_all()
                db.create_all()
                print('Database reset successfully')
            except Exception as reset_error:
                print(f'Failed to reset database: {reset_error}')
    
    app.run(debug=True, host='0.0.0.0', port=5000)

