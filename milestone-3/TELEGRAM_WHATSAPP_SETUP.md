# Telegram and WhatsApp Integration Guide

## Overview

This document explains how to integrate Telegram and WhatsApp messaging into the Voice-Based Email Messaging Assistant.

## Architecture

### Platform Adapter Pattern

Both Telegram and WhatsApp follow the same platform adapter pattern:

1. **Type Definitions** (`*Types.ts`) - Define interfaces for messages, configurations, etc.
2. **Client Wrapper** (`*Client.ts`) - Handles API communication
3. **Platform Adapter** (`*Adapter.ts`) - Implements the `PlatformAdapter` interface for action routing

### Supported Actions

#### Telegram
- **READ**: Fetch and read messages from a chat
- **SEND**: Send a new message to a contact
- **REPLY**: Reply to a specific message
- **OPEN_PLATFORM**: Connect/authenticate with Telegram
- **DRAFT**: Compose a draft message (future)
- **SUMMARIZE**: Summarize conversation (future)

#### WhatsApp
- **READ**: Fetch and read messages from a contact
- **SEND**: Send a new message via WhatsApp
- **REPLY**: Reply to a message
- **DRAFT**: Compose a draft message
- **OPEN_PLATFORM**: Initialize WhatsApp connection
- **SUMMARIZE**: Summarize conversation (future)

## Setup Instructions

### Telegram Setup

#### 1. Get Telegram API Credentials

1. Go to [Telegram's API Development Tools](https://my.telegram.org)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy your `api_id` and `api_hash`

#### 2. Configure Environment Variables

Create or update your `.env` file:

```bash
VITE_TELEGRAM_API_ID=your_api_id_here
VITE_TELEGRAM_API_HASH=your_api_hash_here
VITE_TELEGRAM_PHONE_NUMBER=+1234567890
VITE_TELEGRAM_SESSION_NAME=telegram_session
```

#### 3. Initialize Telegram Client

```typescript
import { getTelegramClient } from "@/lib/telegram/telegramClient";

const client = getTelegramClient({
  apiId: parseInt(import.meta.env.VITE_TELEGRAM_API_ID),
  apiHash: import.meta.env.VITE_TELEGRAM_API_HASH,
  phoneNumber: import.meta.env.VITE_TELEGRAM_PHONE_NUMBER,
  sessionName: import.meta.env.VITE_TELEGRAM_SESSION_NAME
});

await client.connect();
```

### WhatsApp Setup (Twilio)

#### 1. Create Twilio Account

1. Sign up at [Twilio.com](https://www.twilio.com)
2. Verify your phone number
3. Get your Account SID and Auth Token from the dashboard

#### 2. Set Up WhatsApp Messaging

1. Go to Twilio Console → Messaging → Services
2. Create a new Messaging Service or use WhatsApp API
3. Get your WhatsApp Number (or use sandbox number for testing)

#### 3. Configure Environment Variables

```bash
VITE_TWILIO_ACCOUNT_SID=your_account_sid_here
VITE_TWILIO_AUTH_TOKEN=your_auth_token_here
VITE_TWILIO_WHATSAPP_PHONE_NUMBER=+14155552671
VITE_TWILIO_WEBHOOK_URL=https://your-webhook-url.com/whatsapp/webhook
```

#### 4. Initialize WhatsApp Client

```typescript
import { getWhatsAppClient } from "@/lib/whatsapp/whatsappClient";

const client = getWhatsAppClient({
  accountSid: import.meta.env.VITE_TWILIO_ACCOUNT_SID,
  authToken: import.meta.env.VITE_TWILIO_AUTH_TOKEN,
  whatsappPhoneNumber: import.meta.env.VITE_TWILIO_WHATSAPP_PHONE_NUMBER,
  webhookUrl: import.meta.env.VITE_TWILIO_WEBHOOK_URL
});
```

## Usage Examples

### Voice Commands for Telegram

```
"Open Telegram"
"Check Telegram messages"
"Read Telegram"
"Send message on Telegram to John: Hello John!"
"Reply on Telegram: Thanks for the message"
```

### Voice Commands for WhatsApp

```
"Open WhatsApp"
"Check WhatsApp messages"
"Read WhatsApp from +1234567890"
"Send WhatsApp message to Maria: Hi Maria!"
"WhatsApp message: Can you call me later?"
"Reply on WhatsApp: Sure, will do!"
```

## Intent Recognition

The system automatically recognizes platform-specific intents:

```typescript
// Examples of intent detection
"read telegram" → { action: "READ", platform: "telegram" }
"send whatsapp to john" → { action: "SEND", platform: "whatsapp" }
"reply on telegram" → { action: "REPLY", platform: "telegram" }
```

## File Structure

```
src/lib/
├── telegram/
│   ├── telegramTypes.ts      # Type definitions
│   ├── telegramClient.ts     # Client wrapper
│   └── telegramAdapter.ts    # Platform adapter
├── whatsapp/
│   ├── whatsappTypes.ts      # Type definitions
│   ├── whatsappClient.ts     # Twilio wrapper
│   └── whatsappAdapter.ts    # Platform adapter
└── platforms/
    ├── platformTypes.ts      # Platform interface
    ├── platformRegistry.ts   # Platform registry
    ├── platformRouter.ts     # Intent router
    └── init.ts              # Platform initialization
```

## Advanced Features

### Message Formatting

Both adapters support formatted messages:

- **Telegram**: Supports markdown and HTML formatting
- **WhatsApp**: Supports WhatsApp message formatting

### Media Support

```typescript
// WhatsApp media messages
const result = await client.sendMediaMessage(
  "+1234567890",
  "https://example.com/image.jpg",
  "Check this out!"
);
```

### Message History

```typescript
// Fetch conversation history
const messages = await telegramClient.getMessages(chatId, 10);
const messages = await whatsappClient.getMessageHistory(phoneNumber, 5);
```

## Error Handling

Both adapters implement comprehensive error handling:

```typescript
const result = await adapter.execute(intent);

if (!result.success) {
  console.error("Error:", result.error);
  console.log("Message:", result.message);
}
```

## Testing

### Test Telegram Adapter

```typescript
import { TelegramAdapter } from "@/lib/telegram/telegramAdapter";

const intent = {
  action: "SEND",
  platform: "telegram",
  text: "Send message on telegram to john",
  entities: { to: "john", body: "Hello!" }
};

const result = await TelegramAdapter.execute(intent);
```

### Test WhatsApp Adapter

```typescript
import { WhatsAppAdapter } from "@/lib/whatsapp/whatsappAdapter";

const intent = {
  action: "SEND",
  platform: "whatsapp",
  text: "send whatsapp to maria",
  entities: { to: "+1234567890", body: "Hi!" }
};

const result = await WhatsAppAdapter.execute(intent);
```

## Future Enhancements

- [ ] Message summarization using AI
- [ ] Voice message support (audio recording and playback)
- [ ] Group chat support
- [ ] Media sharing and file attachment
- [ ] End-to-end encryption for Telegram
- [ ] Webhook integration for real-time message updates
- [ ] Contact management and favorites
- [ ] Message search functionality
- [ ] Notification handling

## Troubleshooting

### Telegram Connection Issues

1. Verify API credentials are correct
2. Check internet connection
3. Ensure session file has proper permissions
4. Review Telethon documentation

### WhatsApp Twilio Issues

1. Verify Account SID and Auth Token
2. Check WhatsApp sandbox setup
3. Verify phone number format (+country_code format)
4. Review Twilio logs for errors

## References

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telethon Documentation](https://docs.telethon.dev)
- [Twilio WhatsApp API](https://www.twilio.com/whatsapp)
- [Twilio Python SDK](https://github.com/twilio/twilio-python)
