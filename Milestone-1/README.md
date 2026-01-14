# Voice-Based Email & Messaging Assistant

A 100% hands-free voice-driven assistant for email and messaging management, designed with accessibility and inclusivity in mind.

## Milestone 1: Authentication & Profile Management ✅ COMPLETE

This milestone includes:
- ✅ User registration/login with face biometric authentication
- ✅ Google OAuth integration with face verification
- ✅ Profile management (language, voice preferences, biometric data)
- ✅ Voice command recognition (basic commands)
- ✅ 100% hands-free voice-driven interface
- ✅ Face-only authentication (no password required)

## Features

### ✅ Authentication Methods (Fully Implemented)
1. **Local Registration/Login** - Email and password-based authentication
2. **Google OAuth** - One-click Google sign-in integration
3. **Face Recognition Login** - Hands-free biometric login with no password required
4. **Face-Only Login** - Direct face recognition for registered users

### ✅ Face Recognition & Biometric Security (Fully Implemented)
- **Face Registration** - Mandatory during account creation using face-api.js
- **Face Verification** - Required during login and OAuth processes
- **Face Descriptors Storage** - Euclidean distance-based face matching (threshold: 0.6)
- **Face Image Storage** - Profile pictures saved securely
- **Face-Only Authentication** - Login with just face recognition, no credentials needed

### ✅ Profile Management (Fully Implemented)
- **Language selection** - English, Spanish, French, German, Hindi
- **Voice speed control** - Adjustable range (0.5x - 2.0x)
- **Voice pitch control** - Adjustable range (0.5 - 2.0)
- **Voice name/preference** - Select preferred voice
- **Messaging platforms** - Store connected platforms
- **Preferences storage** - JSON-based preference persistence

### ✅ Voice Recognition & Processing (Fully Implemented)
- **Web Speech API Integration** - Browser-based voice recognition
- **Voice Command Recognition** - Process natural voice input
- **Text-to-Speech Synthesis** - Automated voice responses
- **Speech Recognition Endpoint** - `/api/voice/recognize` for voice processing
- **Voice Processing Pipeline** - Real-time voice command handling

### ✅ Voice-Based Security (Fully Implemented)
- **Voice PIN Setup** - Create custom voice-based security PIN
- **Voice PIN Verification** - Authenticate using spoken PIN
- **Voice PIN Check** - Verify if user has voice PIN configured

### ✅ Voice Commands
- **"Hello"** - Greeting
- **"Login"** - Sign in
- **"Register"** - Create account
- **"Profile"** - View settings
- **"Logout"** - Sign out
- **"Help"** - Show available commands
- **"Test"** - Test voice recognition

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Chrome, Edge, or Safari browser (for Web Speech API support)
- (Optional) Docker for containerized deployment

### Setup Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd "voice assistant"
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   copy .env.example .env  # Windows
   # or
   cp .env.example .env    # macOS/Linux
   
   # Edit .env and add your credentials (optional for basic testing)
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   - Navigate to `http://localhost:5000`
   - Use Chrome, Edge, or Safari for best voice recognition support

### Running with Docker

1. **Build the Docker image**
   ```bash
   docker build -t voice-assistant .
   ```

2. **Run the container**
   ```bash
   docker run -p 5000:5000 -v $(pwd)/instance:/app/instance voice-assistant
   ```

3. **Access the application**
   - Open `http://localhost:5000` in your browser

**Note:** On Windows, use the provided `docker-quickstart.ps1` script for easier setup.

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///voice_assistant.db

# Google OAuth (Optional - for Google login)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Security
TALISMAN_ENABLED=False  # Set to True for production

# Flask Environment
FLASK_ENV=development
FLASK_DEBUG=True
```

### OAuth Setup (Optional)

### Google OAuth Setup (Optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:5000/auth/google/callback`
6. Copy Client ID and Client Secret to `.env` file
7. (Optional) Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`

**Note:** OAuth is optional. You can use local registration/login or face-only login without OAuth setup.

### Face Recognition Setup
- Face recognition uses face-api.js which downloads models on first load
- Models include: face detection, landmarks, recognition, and expression
- Approximately 30-50MB of model data cached in browser
- No additional setup required - automatic on first use

## Quick Start

**Fastest way to get running:**
```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run the app
python app.py

# Open http://localhost:5000 in Chrome/Edge/Safari
```

**First-time experience:**
1. Click the 🎤 microphone button
2. Say **"register"** to create an account with face biometric
3. Or say **"login"** if you already have an account
4. Use **"help"** to see available voice commands

## Usage

### Getting Started
1. Open the application in your browser at `http://localhost:5000`
2. You'll see the main voice interface with a microphone button
3. Click the microphone button or say the wake word to activate voice recognition
4. Choose an action: **"register"**, **"login"**, or **"help"**
5. Follow the voice-guided prompts

### Authentication Flow
**Registration:**
1. Say **"register"** or click the register button
2. Enter your name, email, and password
3. Capture your face using your camera (mandatory for biometric security)
4. Face registration is verified and saved
5. Account created successfully!

**Traditional Login:**
1. Say **"login"** or click the login button
2. Enter your email and password
3. Capture your face for verification
4. Face must match registered face to complete login
5. Dashboard is accessible after successful authentication

**Face-Only Login (New):**
1. Say **"login"** or click the login button
2. Click the "Login with Face" button
3. Capture your face and the system instantly recognizes you
4. No email or password required!
5. Direct access to your dashboard

**Google OAuth Login:**
1. Click **"Login with Google"** button
2. Sign in with your Google account
3. For first-time users: Capture your face for registration
4. For returning users: Verify your face to complete login
5. Account linked and logged in!

### Voice Navigation
- The interface is 100% hands-free
- Use wake words: **"start listening"**, **"hey assistant"**, or **"wake up"**
- Voice commands work naturally - no special syntax needed
- All responses are read aloud automatically using text-to-speech
- Transcribed text displays in real-time

### Profile Settings
- Say **"profile"** to access your preferences
- Adjust language, voice speed, and pitch
- Configure voice PIN for additional security
- Enable/disable messaging platform connections
- All changes saved automatically to your profile

## Project Structure

```
voice based assistant/
├── app.py                          # Flask backend with authentication & API endpoints
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker containerization
├── docker-quickstart.ps1          # Docker startup script
├── README.md                       # Project documentation
├── templates/
│   └── index.html                 # Frontend interface with voice UI & face recognition
├── static/
│   ├── css/
│   │   └── style.css             # Styling for voice interface
│   ├── js/
│   │   └── face-api.min.js       # Face detection & recognition library
│   ├── models/                   # Pre-trained face models (landmarks, detection, recognition)
│   │   ├── tiny_face_detector_model-weights_manifest.json
│   │   ├── face_landmark_68_model-weights_manifest.json
│   │   ├── face_recognition_model-weights_manifest.json
│   │   └── face_expression_model-weights_manifest.json
│   └── faces/                    # User face images storage
├── docs/
│   ├── COMPLETE_PROJECT_GUIDE.md # Comprehensive project documentation
│   └── overview.md               # Project overview
├── tests/
│   ├── test_authentication.py    # Authentication tests
│   └── __init__.py
├── face_env/                     # Python virtual environment
├── flask_session/                # Flask session storage
├── backups/                      # Database backups
└── __pycache__/                  # Python cache files
```

## Technology Stack

- **Backend:** Flask 3.0+ (Python web framework)
- **Database:** SQLite with SQLAlchemy ORM
- **Frontend:** HTML5, CSS3, JavaScript
- **Voice Recognition:** Web Speech API (browser-based, works on Chrome/Edge/Safari)
- **Text-to-Speech:** Web Speech Synthesis API
- **Face Recognition:** face-api.js with TensorFlow.js
  - Tiny Face Detector for face detection
  - Face Landmark Detection (68 points)
  - Face Recognition Model (128-d descriptors)
  - Face Expression Detection
- **Authentication:** 
  - Local authentication with bcrypt password hashing
  - Google OAuth 2.0 integration
  - Biometric face recognition (Euclidean distance matching)
- **Security:**
  - Werkzeug password hashing (PBKDF2)
  - Session management (Flask-Session with filesystem backend)
  - CORS enabled for API security
  - Talisman for HTTPS/CSP (optional for local dev)
- **Testing:** pytest with coverage reporting
- **Containerization:** Docker support for easy deployment

## API Endpoints

### Authentication Endpoints
- `GET /api/auth/status` - Check current authentication status
- `POST /api/auth/register` - Register new user with face biometric
- `POST /api/auth/login` - Email/password login (requires face verification)
- `POST /api/auth/verify-face-login` - Verify face recognition during login
- `POST /api/auth/face-login` - Direct face-only login (no credentials)
- `POST /api/auth/logout` - Clear session and logout
- `GET /api/auth/face-status` - Check if user has face registered

### OAuth Endpoints
- `GET /auth/google` - Initiate Google OAuth flow
- `GET /auth/google/callback` - OAuth callback handler
- `GET /api/auth/oauth-pending-status` - Check pending OAuth login status
- `POST /api/auth/complete-oauth-face-registration` - Register face for new OAuth users
- `POST /api/auth/complete-oauth-face-verification` - Verify face for returning OAuth users

### Profile Endpoints
- `GET /api/profile` - Retrieve user profile and preferences
- `PUT /api/profile` - Update profile settings

### Voice Endpoints
- `POST /api/voice/process` - Process voice input
- `POST /api/voice/recognize` - Voice recognition and command processing
- `POST /api/voice-pin/setup` - Create custom voice PIN
- `POST /api/voice-pin/verify` - Verify spoken voice PIN
- `GET /api/voice-pin/check` - Check if user has voice PIN configured

### Face Recognition Endpoints
- `POST /api/face/verify` - Verify face recognition match

### Admin Endpoints
- `POST /api/admin/reset-db` - Reset database (development only)

## Browser Compatibility

- ✅ Chrome/Chromium (recommended) - Full support
- ✅ Microsoft Edge - Full support
- ✅ Safari - Full support (iOS 14.5+)
- ⚠️ Firefox - Limited Web Speech API support
- ⚠️ Mobile Browsers - Variable support for Web Speech API

## Next Milestones

### Milestone 2 (In Development)
- Email Integration (Gmail API)
- Messaging Integration (WhatsApp, Telegram)
- Voice-based email reading and composition
- Message transcription and voice replies

### Milestone 3 (Planned)
- Email/message summarization with AI
- Smart reply suggestions
- Natural language understanding enhancements
- Multi-language support expansion

### Milestone 4 (Planned)
- Admin dashboard and user management
- Advanced security features (2FA, encryption)
- Production deployment and scaling
- Performance optimization
- Analytics and monitoring

## Development Status

**Current Sprint:** Milestone 1 Complete, Milestone 2 In Progress

### Completed Features ✅
- User authentication (local, Google OAuth, biometric)
- Face recognition and verification
- Profile management with voice preferences
- Voice command recognition
- Voice PIN setup and verification
- 100% hands-free interface
- Real-time voice transcription and synthesis

### In Development 🔄
- Email integration with Gmail API
- Messaging platform connections

### Planned Features 📋
- Email management (read, send, organize)
- Message management (read, send, organize)
- AI-powered summarization
- Smart reply generation
- Advanced analytics

## Troubleshooting

### Voice Recognition Not Working
- Ensure you're using Chrome, Edge, or Safari (Firefox has limited support)
- Check microphone permissions in browser settings
- Make sure you're using HTTPS or localhost (required for Web Speech API)
- Try refreshing the page and allowing microphone access again
- Test microphone in browser DevTools Console first

### Face Recognition Issues
- Ensure adequate lighting in your environment (face-api.js needs clear visibility)
- Position your face directly toward the camera (front-facing)
- Avoid wearing sunglasses or face coverings during registration
- Make sure your camera has proper focus and resolution
- Face capture requires modern browser support for Canvas API

### Face Verification Failing
- Try repositioning your face relative to the camera
- Ensure lighting conditions are similar to registration
- Use the "Retake" button to capture a fresh image
- Descriptor distance threshold is 0.6 - if consistently failing, retake face photo
- Check browser console for detailed distance measurements

### OAuth Not Working
- Verify OAuth credentials in `.env` file (if using)
- Check redirect URIs match exactly in OAuth app settings
- Ensure OAuth apps are properly configured in Google Cloud Console
- For local development, use `http://localhost:5000` (not https)
- Clear browser cookies and session if stuck in OAuth flow

### Database Issues
- Delete `voice_assistant.db` to reset the database (all data will be lost)
- The database is created automatically on first run
- Use `/api/admin/reset-db` endpoint to reset database (development only)
- Check database file permissions if getting write errors

### Audio/Speech Output Not Working
- Check browser volume settings and mute status
- Verify text-to-speech is enabled in browser
- Try different voice selections in profile settings
- Check for browser notifications/speech permissions
- On iOS Safari, speech synthesis requires user interaction

### Camera/Microphone Permissions
- **Chrome/Edge:** Settings → Privacy and security → Site settings → Camera/Microphone
- **Safari:** System Preferences → Security & Privacy → Camera/Microphone
- **Firefox:** about:preferences → Privacy & Security → Permissions
- Clear site data and re-grant permissions if issues persist

## Known Issues & Limitations

### Current Limitations
1. **Firefox Support** - Limited Web Speech API support; use Chrome/Edge/Safari
2. **Face Recognition Accuracy** - Performance depends on lighting and camera quality
3. **Voice Recognition** - Accuracy varies by browser and language support
4. **Mobile Browsers** - Web Speech API support varies significantly
5. **Single Device** - Sessions are device/browser specific
6. **No Email/Messaging Yet** - Milestone 2 not yet implemented

### Browser-Specific Issues
- **Safari iOS:** Requires user gesture to start speech recognition
- **Firefox:** Limited Web Speech API - use Chrome for best results
- **Mobile:** Microphone permissions require HTTPS (except localhost)
- **Incognito Mode:** Some browsers restrict microphone access in private browsing

### Performance Notes
- Face recognition model download (~30-50MB) on first load
- Large face descriptor calculations may cause slight delays
- Database growth with user accumulation - consider cleanup for production

## Testing

### Running Tests
```bash
# Run all tests with coverage
pytest tests/ --cov=.

# Run specific test file
pytest tests/test_authentication.py -v

# Run with output
pytest tests/ -s
```

### Manual Testing Checklist
- [ ] Registration with email, password, and face capture
- [ ] Login with email/password and face verification
- [ ] Face-only login without credentials
- [ ] Google OAuth sign-up and login
- [ ] Face verification fails with unrecognized face
- [ ] Voice commands work (hello, help, profile, logout)
- [ ] Profile settings save correctly
- [ ] Voice PIN setup and verification
- [ ] Voice speed and pitch adjustments
- [ ] Language selection changes UI/speech
- [ ] Database resets properly with admin endpoint

### Test Accounts (After Reset)
- Create test accounts with various authentication methods
- Use test faces under different lighting conditions
- Verify cross-browser compatibility (Chrome, Edge, Safari)

## Contributing

This is a milestone-based project. Contributions and improvements are welcome!

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Reporting Issues
- Create detailed issue reports with reproduction steps
- Include browser and OS information
- Attach error logs or screenshots when applicable
- Test in Chrome before reporting (as baseline)

## License

This project is open-source and available for educational purposes.

## Support & Contact

For questions, issues, or feature requests:
- Check the [COMPLETE_PROJECT_GUIDE.md](docs/COMPLETE_PROJECT_GUIDE.md) for detailed documentation
- Review the [Troubleshooting](#troubleshooting) section
- Open an issue on the repository
- Check existing issues before creating duplicates

## Changelog

### Version 1.0 (Current)
- ✅ Complete authentication system with biometric security
- ✅ Face recognition and verification
- ✅ Google OAuth integration
- ✅ Voice commands and recognition
- ✅ Profile management
- ✅ Voice PIN security
- ✅ Docker support

### Roadmap
- Milestone 2: Email and messaging integration
- Milestone 3: AI-powered summarization and smart replies
- Milestone 4: Production deployment and analytics

## Project Maintainers

Built with ❤️ for accessibility and inclusivity in communication.


