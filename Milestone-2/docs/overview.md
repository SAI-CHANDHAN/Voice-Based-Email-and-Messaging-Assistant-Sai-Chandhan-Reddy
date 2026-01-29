# Voice Assistant Project Overview

## Stack
- Backend: Flask + Flask-Session + Flask-SQLAlchemy, CORS, Flask-Talisman for CSP/HTTPS, dotenv for env loading.
- Auth: Password + face verification (face-api.js descriptors), Google OAuth with mandatory face biometric integration, optional voice PIN for extra security.
- Frontend: Single-page application (templates/index.html) with Web Speech API for STT/TTS and face-api.js for camera-based face capture. Styles in static/css/style.css.
- Tests: pytest.

## Data model
- User: email (unique), password_hash, name, oauth_provider ('local'/'google'), oauth_id, created_at, one-to-one profile relationship.
- UserProfile: 
  - language, voice_speed/pitch/name (TTS preferences)
  - messaging_platforms (JSON array), preferences (JSON object)
  - face_image_path (JPEG path), face_encoding (JSON list of 128 floats)
  - voice_pin (hashed PIN for extra security)
  - updated_at timestamp

## Core backend routes (app.py)

### Authentication Routes
- **GET /** : Serve index.html single-page application.
- **GET /api/auth/status** : Session check + return authenticated user with profile.
- **POST /api/auth/register** : Register with name/email/password + face_image (base64) + face_descriptors array; validates all fields, hashes password, saves face image to disk, stores 128-float descriptor in database.
- **POST /api/auth/login** : Verify email/password; checks if face registered; returns `requires_face_verification: true` flag to trigger face capture on frontend.
- **POST /api/auth/verify-face-login** : Compare incoming face descriptors (128 floats) vs stored using Euclidean distance; creates session if distance < 0.6.
- **POST /api/auth/face-login** : Pure face-based login (no email/password); matches captured face against all registered users; returns best match if distance < 0.6.
- **GET /api/auth/face-status** : Check if current session user has face enrolled.
- **POST /api/auth/logout** : Clear session.

### OAuth Routes (Google)
- **GET /auth/google** : Initiate Google OAuth flow; redirects to Google login.
- **GET /auth/google/callback** : OAuth callback; exchanges code for token; creates/updates user; checks face status:
  - **New user (no face)** → Sets pending flag, redirects with `face_registration_required=true`
  - **Returning user (has face)** → Sets pending flag, redirects with `face_verification_required=true`

### OAuth Face Completion Routes
- **GET /api/auth/oauth-pending-status** : Check if OAuth login pending + what action needed.
- **POST /api/auth/complete-oauth-face-registration** : Register face for new OAuth user (from pending session).
- **POST /api/auth/complete-oauth-face-verification** : Verify face for returning OAuth user (from pending session).

### Voice PIN Routes
- **POST /api/voice-pin/setup** : Hash and store voice PIN (4+ digits) for additional authentication layer.
- **POST /api/voice-pin/verify** : Verify voice PIN for passwordless login alternative.
- **GET /api/voice-pin/check** : Check if user has voice PIN registered.

### Profile & Settings Routes
- **GET /api/profile** : Fetch user profile + preferences (language, voice speed/pitch, messaging platforms).
- **PUT /api/profile** : Update profile (language, voice settings, preferences).

### Voice Processing Routes
- **POST /api/voice/process** : Intent classification on voice command text (calls VoiceCommandProcessor); returns action + response message.
- **POST /api/voice/recognize** : Server-side STT fallback using SpeechRecognition library (if client-side fails).
- **POST /api/face/verify** : Alternate face verification endpoint (email-based).

### Admin Routes
- **POST /api/admin/reset-db** : Dev-only database reset (disabled in production).

## Frontend flow (templates/index.html)

### State Machine
- **IDLE** → Waiting for wake word "aira"
- **AWAKE** → Wake word detected, greeting spoken
- **LISTENING_FOR_COMMAND** → Listening for login/register/logout
- **WAITING_EMAIL/PASSWORD/NAME** → Collecting credentials voice-by-voice
- **WAITING_REG_EMAIL/REG_PASSWORD** → Registration credential collection
- **WAITING_FACE_CAPTURE** → Face capture in progress
- **LOGGED_IN** → User authenticated, dashboard visible

### Registration Flow
1. Voice: "register" detected
2. Prompt for name, email, password (one-by-one via voice)
3. Camera activates for face capture
4. face-api.js extracts 128-dimensional descriptor
5. POST /api/auth/register with all data + base64 face image
6. Backend saves face to disk, stores descriptor in DB
7. Redirect to login flow

### Local Login Flow (Email + Password + Face)
1. Voice: "login" detected
2. Prompt for email, password via voice
3. POST /api/auth/login (password verification only)
4. If `requires_face_verification`: Camera activates
5. POST /api/auth/verify-face-login with captured descriptors
6. On match: Session created, dashboard shown

### Google OAuth Flow (New User)
1. Voice: "login with google" OR Button click
2. Redirect to /auth/google
3. User authenticates with Google
4. Callback creates user record
5. Frontend detects pending OAuth + face registration required
6. Camera activates for face registration
7. POST /api/auth/complete-oauth-face-registration
8. Dashboard shown

### Google OAuth Flow (Returning User)
1-4. Same as new user
5. Frontend detects pending OAuth + face verification required
6. Camera activates for face verification
7. POST /api/auth/complete-oauth-face-verification
8. Dashboard shown

### Face-Only Login (New Feature)
1. User clicks "Face Login"
2. Camera activates
3. POST /api/auth/face-login with descriptors
4. Backend finds best match among all users
5. If match confidence > 40% (distance < 0.6):
   - Session created
   - Welcome message with name
6. Else: Show error, allow retry or email/password login

### Dashboard
- Calls /api/auth/status + /api/profile
- Shows user profile info
- Loads voice preferences (speed, pitch, language)
- Allows preferences update via updatePreference()
- Logout button available

## Key features & libraries

### Backend Features
- **Password Security**: Werkzeug PBKDF2-SHA256 hashing with per-password salts
- **Face Matching**: Euclidean distance (128-dimensional descriptors) with 0.6 threshold
- **Session Management**: Flask-Session with server-side storage (filesystem)
- **CORS**: Flask-CORS allows cross-origin API calls from frontend
- **OAuth 2.0**: google-auth-oauthlib for Google authentication
- **Image Processing**: Pillow for decoding base64 face images

### Frontend Features
- **Web Speech API**: SpeechRecognition (STT) + speechSynthesis (TTS)
  - Supports 100+ languages
  - Server-side fallback available
- **face-api.js**: 
  - TinyFaceDetector for face detection
  - FaceRecognitionNet for 128-D descriptor extraction
  - Loaded from CDN (no local ML models needed)
- **Canvas API**: Frame capture for face processing
- **State Machine**: Guides conversation flow + UI visibility
- **Multi-language**: TRANSLATIONS object + language-specific command keywords

### Security Features
- Password hashing (Werkzeug)
- Session-based authentication (server-side)
- Face verification mandatory (biometric second factor)
- Optional voice PIN for extra security
- OAuth state parameter for CSRF prevention
- Base64 face image handling (no direct file uploads)

## Run quickstart
```bash
python app.py
```
Then navigate to http://localhost:5000

## Configuration
- .env file required with:
  - `SECRET_KEY`: Flask session key
  - `DATABASE_URL`: SQLite path (default: sqlite:///voice_assistant.db)
  - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`: OAuth credentials
  - `TALISMAN_ENABLED`: Set to 'false' for local development (default: 'true')

## Notes for presentation
- **Security**: Two-factor auth (password + face), biometric descriptors are one-way, salted password hashing, session-based auth.
- **Biometric**: Face descriptors stored as JSON arrays (128 floats); Euclidean distance < 0.6 indicates match.
- **OAuth Integration**: Mandatory face registration/verification for both new and returning OAuth users.
- **Face-Only Login**: New feature enabling quick biometric-only authentication (hands-free).
- **Voice PIN**: Optional additional security layer (4+ digit PIN hashed and verified).
- **Storage**: Face images in static/faces/, face encodings in database as JSON.
- **Voice UX**: State machine guides flow; multi-language support; fallback to email/password if voice fails.
- **Dev Tools**: /api/admin/reset-db for development schema rebuilds; Talisman CSP configuration included.
