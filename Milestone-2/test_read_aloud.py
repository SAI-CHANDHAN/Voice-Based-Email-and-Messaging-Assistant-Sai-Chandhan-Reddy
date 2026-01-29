#!/usr/bin/env python3
"""Test script to verify read aloud functionality"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from tts_service import get_tts_service

def test_read_email():
    """Test the read_email method"""
    print("Testing TTS read_email functionality...")
    
    # Sample email data
    email_data = {
        'id': 'test_email_1',
        'subject': 'Test Email Subject',
        'from': 'John Doe <john@example.com>',
        'to': 'recipient@example.com',
        'date': 'Mon, 20 Jan 2025 10:30:00 +0000',
        'body': 'This is a test email body. It contains some text to test the read aloud functionality.',
        'snippet': 'This is a test email body...'
    }
    
    # Get TTS service
    tts = get_tts_service()
    print(f"TTS Engine Type: {tts.engine_type}")
    print(f"TTS Voice ID: {tts.voice_id}")
    print(f"TTS Rate: {tts.rate}")
    print(f"TTS Volume: {tts.volume}")
    
    # Test read_email
    print("\nCalling read_email()...")
    result = tts.read_email(email_data, include_body=True)
    print(f"Result: {result}")
    
    if result:
        print("Test passed!")
    else:
        print("Test failed!")
        
    return result

if __name__ == '__main__':
    with app.app_context():
        success = test_read_email()
        sys.exit(0 if success else 1)
