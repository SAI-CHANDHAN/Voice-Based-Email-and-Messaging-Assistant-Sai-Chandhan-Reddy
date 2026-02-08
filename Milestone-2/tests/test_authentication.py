"""
Unit tests for Authentication & Voice Commands (Module 1 & 2, Milestone 1)
"""
import unittest
import json
from app import app, db, User, UserProfile
from werkzeug.security import check_password_hash, generate_password_hash


class AuthenticationTestCase(unittest.TestCase):
    """Test authentication functionality"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        response = self.client.post('/api/auth/register', 
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['email'], 'test@example.com')
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        # First registration
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        # Duplicate registration
        response = self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password456',
                'name': 'Another User'
            })
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already registered', data['error'])
    
    def test_user_login_success(self):
        """Test successful user login with password"""
        # Register user
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        # Login
        response = self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['method'], 'password')
    
    def test_user_login_invalid_password(self):
        """Test login with incorrect password"""
        # Register user
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        # Login with wrong password
        response = self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'wrongpassword'
            })
        
        self.assertEqual(response.status_code, 401)
    
    def test_auth_status_authenticated(self):
        """Test checking auth status when authenticated"""
        # Register and login
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        # Check status
        response = self.client.get('/api/auth/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['email'], 'test@example.com')
    
    def test_auth_status_unauthenticated(self):
        """Test checking auth status when not authenticated"""
        response = self.client.get('/api/auth/status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['authenticated'])
    
    def test_logout(self):
        """Test logout functionality"""
        # Register and login
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        # Logout
        response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 200)
        
        # Verify logged out
        response = self.client.get('/api/auth/status')
        data = json.loads(response.data)
        self.assertFalse(data['authenticated'])


class ProfileTestCase(unittest.TestCase):
    """Test profile management functionality"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            # Create a test user
            user = User(
                email='test@example.com',
                password_hash=generate_password_hash('password123'),
                name='Test User',
                oauth_provider='local'
            )
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_get_profile(self):
        """Test retrieving user profile"""
        # Login
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.get('/api/profile')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('language', data)
        self.assertIn('voice_speed', data)
    
    def test_update_language_preference(self):
        """Test updating language preference"""
        # Login
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.put('/api/profile',
            json={'language': 'hi-IN'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_update_voice_settings(self):
        """Test updating voice speed and pitch"""
        # Login
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        response = self.client.put('/api/profile',
            json={
                'voice_speed': 1.5,
                'voice_pitch': 0.8
            })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify changes
        response = self.client.get('/api/profile')
        data = json.loads(response.data)
        self.assertEqual(data['voice_speed'], 1.5)
        self.assertEqual(data['voice_pitch'], 0.8)


class VoiceCommandTestCase(unittest.TestCase):
    """Test voice command processing (Module 2)"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_greeting_command(self):
        """Test greeting command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'hello'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'greeting')
        self.assertGreater(data['confidence'], 0.5)
    
    def test_login_command(self):
        """Test login command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'login'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'login')
    
    def test_register_command(self):
        """Test register command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'sign up'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'register')
    
    def test_google_login_command(self):
        """Test Google login command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'login with google'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'login_google')
        self.assertIn('redirect', data)
    
    def test_help_command(self):
        """Test help command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'help'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'help')
    
    def test_logout_command(self):
        """Test logout command recognition"""
        response = self.client.post('/api/voice/process',
            json={'text': 'logout'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'logout')
    
    def test_unknown_command(self):
        """Test unknown command handling"""
        response = self.client.post('/api/voice/process',
            json={'text': 'something random that makes no sense'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['action'], 'unknown')


class VoicePINTestCase(unittest.TestCase):
    """Test Voice PIN authentication (Module 1)"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            # Create and login a test user
            user = User(
                email='test@example.com',
                password_hash=generate_password_hash('password123'),
                name='Test User',
                oauth_provider='local'
            )
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_setup_voice_pin(self):
        """Test setting up a voice PIN"""
        # Login first
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        # Setup voice PIN
        response = self.client.post('/api/voice-pin/setup',
            json={'voice_pin': '1234'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_voice_pin_too_short(self):
        """Test voice PIN validation (minimum 4 digits)"""
        # Login first
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        # Try to setup short PIN
        response = self.client.post('/api/voice-pin/setup',
            json={'voice_pin': '12'})
        
        self.assertEqual(response.status_code, 400)
    
    def test_verify_voice_pin(self):
        """Test verifying voice PIN for login"""
        # Setup voice PIN
        with app.app_context():
            user = User.query.get(self.user_id)
            if not user.profile:
                user.profile = UserProfile(user_id=user.id)
            user.profile.voice_pin = generate_password_hash('1234')
            db.session.commit()
        
        # Verify PIN
        response = self.client.post('/api/voice-pin/verify',
            json={
                'email': 'test@example.com',
                'voice_pin': '1234'
            })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])


class FaceVerificationTestCase(unittest.TestCase):
    """Test face verification functionality (Extra Feature)"""
    
    def setUp(self):
        """Set up test client and database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_check_face_status_unauthenticated(self):
        """Test checking face status when not authenticated"""
        response = self.client.get('/api/auth/face-status')
        self.assertEqual(response.status_code, 401)
    
    def test_check_face_status_no_face_registered(self):
        """Test checking face status when no face is registered"""
        # Register and login
        self.client.post('/api/auth/register',
            json={
                'email': 'test@example.com',
                'password': 'password123',
                'name': 'Test User'
            })
        
        self.client.post('/api/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        # Check face status
        response = self.client.get('/api/auth/face-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['authenticated'])
        self.assertFalse(data['has_face'])


if __name__ == '__main__':
    unittest.main()
