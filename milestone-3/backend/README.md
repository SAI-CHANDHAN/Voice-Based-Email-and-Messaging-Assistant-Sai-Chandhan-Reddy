# Telegram Backend Setup

## Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

## Start Backend Server

```powershell
python app.py
```

The backend will run on `http://localhost:5001`

## Environment Variables

Make sure your `.env` file in the milestone-3 root contains:

```
VITE_TELEGRAM_API_ID=39556869
VITE_TELEGRAM_API_HASH=623dfa52956158eab315e42c267d2606
VITE_TELEGRAM_PHONE_NUMBER=+919133437430
VITE_TELEGRAM_SESSION_NAME=telegram_session
```

## Authentication Flow

1. Backend will send a verification code to your Telegram app
2. Enter the code in the frontend
3. Session will be saved for future use
