# Telegram & WhatsApp Integration - Quick Reference

## 🚀 5-Minute Setup

### 1. Get API Credentials
- **Telegram**: Visit [my.telegram.org](https://my.telegram.org) → API development tools
- **WhatsApp**: Sign up at [Twilio.com](https://www.twilio.com) → Get Account SID & Auth Token

### 2. Set Environment Variables
```bash
# Telegram
VITE_TELEGRAM_API_ID=your_api_id
VITE_TELEGRAM_API_HASH=your_api_hash
VITE_TELEGRAM_PHONE_NUMBER=+1234567890

# WhatsApp (Twilio)
VITE_TWILIO_ACCOUNT_SID=your_account_sid
VITE_TWILIO_AUTH_TOKEN=your_auth_token
VITE_TWILIO_WHATSAPP_PHONE_NUMBER=+14155552671
```

### 3. Initialize in App
```typescript
import { initPlatforms } from '@/lib/platforms/init';
import { messagingPlatformService } from '@/services/messagingPlatformService';

// During app startup
initPlatforms();
await messagingPlatformService.initializeFromEnv();
```

### 4. Use Voice Commands
```
"Send Telegram to John: Hello"
"Read WhatsApp messages"
"Reply on Telegram: Thanks!"
```

---

## 📁 File Structure

```
milestone-3/
├── src/lib/
│   ├── telegram/
│   │   ├── telegramTypes.ts      (Types & interfaces)
│   │   ├── telegramClient.ts     (Telethon wrapper)
│   │   └── telegramAdapter.ts    (Platform adapter)
│   ├── whatsapp/
│   │   ├── whatsappTypes.ts      (Types & interfaces)
│   │   ├── whatsappClient.ts     (Twilio wrapper)
│   │   └── whatsappAdapter.ts    (Platform adapter)
│   └── platforms/
│       └── init.ts               (⚡ Updated to register both)
├── src/services/
│   └── messagingPlatformService.ts (🆕 New service layer)
├── src/test/
│   └── telegram_whatsapp.test.ts (🆕 Test suite)
├── src/lib/govind/
│   └── intentMap.ts              (⚡ Updated with new intents)
├── TELEGRAM_WHATSAPP_SETUP.md    (📖 Detailed guide)
├── INTEGRATION_SUMMARY.md        (📖 Overview & architecture)
└── package.json                  (⚡ Added telethon & twilio)
```

---

## 💬 Voice Command Examples

### Telegram
| Command | Action |
|---------|--------|
| "Open Telegram" | Connect & authenticate |
| "Check Telegram messages" | Read recent messages |
| "Send Telegram to John: Hi!" | Send message |
| "Reply on Telegram: Thanks!" | Reply to message |

### WhatsApp
| Command | Action |
|---------|--------|
| "Open WhatsApp" | Initialize connection |
| "Check WhatsApp messages" | Read recent messages |
| "Send WhatsApp to +1234567890: Hi!" | Send message |
| "Draft WhatsApp message: Call me" | Create draft |
| "Reply on WhatsApp: Sure" | Reply to message |

---

## 🔌 API Integration Points

### Telegram (Telethon-like)
```typescript
import { getTelegramClient } from '@/lib/telegram/telegramClient';

const client = getTelegramClient(config);
await client.connect();
await client.sendMessage(chatId, "Hello");
const messages = await client.getMessages(chatId, limit);
```

### WhatsApp (Twilio)
```typescript
import { getWhatsAppClient } from '@/lib/whatsapp/whatsappClient';

const client = getWhatsAppClient(config);
await client.sendMessage(phoneNumber, "Hello");
const history = await client.getMessageHistory(phoneNumber);
```

### Service Layer (Recommended)
```typescript
import { messagingPlatformService } from '@/services/messagingPlatformService';

const service = messagingPlatformService;
const status = service.getStatus();
// { telegram: {available, status}, whatsapp: {available, status} }
```

---

## 🎨 Adding New Features

### Add a New Action to Telegram
```typescript
// In telegramAdapter.ts
case "NEW_ACTION": {
  // Your implementation
  return { success: true, message: "Done!" };
}
```

### Add a New Action to WhatsApp
```typescript
// In whatsappAdapter.ts
case "NEW_ACTION": {
  // Your implementation
  return { success: true, message: "Done!" };
}
```

### Add New Intent Pattern
```typescript
// In intentMap.ts
{ 
  action: "READ", 
  platform: "telegram", 
  keywords: ["new telegram keyword", "another synonym"]
}
```

---

## 🧪 Testing

```bash
# Run all tests
npm run test

# Watch mode
npm run test:watch

# Run specific test file
npm run test -- telegram_whatsapp.test.ts
```

### Example Test
```typescript
import { TelegramAdapter } from '@/lib/telegram/telegramAdapter';

const result = await TelegramAdapter.execute({
  action: "SEND",
  platform: "telegram",
  text: "send message on telegram",
  entities: { to: "john", body: "Hello!" }
});

console.log(result); // { success: true, message: "..." }
```

---

## ⚙️ Configuration

### Telegram Config
```typescript
interface TelegramConfig {
  apiId: number;           // From my.telegram.org
  apiHash: string;         // From my.telegram.org
  phoneNumber?: string;    // Your phone number
  sessionName?: string;    // Session storage name
}
```

### WhatsApp Config
```typescript
interface WhatsAppConfig {
  accountSid: string;           // From Twilio Dashboard
  authToken: string;            // From Twilio Dashboard
  whatsappPhoneNumber: string;  // Twilio WhatsApp number
  webhookUrl?: string;          // For real-time updates
}
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "API credentials missing" | Check `.env` file - ensure vars are set |
| "Connection failed" | Verify credentials are correct |
| "Phone number format error" | Use `+` prefix: `+1234567890` |
| "WhatsApp not initialized" | Check Twilio credentials in env |
| "Telegram not responding" | Check internet connection & API status |

---

## 📊 Action Matrix

|Action|Gmail|Telegram|WhatsApp|
|------|-----|--------|--------|
|READ|✅|✅|✅|
|SEND|✅|✅|✅|
|REPLY|✅|✅|✅|
|DRAFT|❌|⚠️|✅|
|SUMMARIZE|✅|⚠️|⚠️|
|OPEN_PLATFORM|✅|✅|✅|

✅ = Implemented  
⚠️ = Ready for implementation  
❌ = Not applicable

---

## 🔗 Key Classes & Functions

### Main Services
- `messagingPlatformService` - Unified platform management
- `TelegramAdapter.execute()` - Execute Telegram actions
- `WhatsAppAdapter.execute()` - Execute WhatsApp actions

### Clients
- `TelegramClient` - Telethon wrapper
- `WhatsAppClient` - Twilio wrapper

### Utilities
- `getTelegramClient()` - Get singleton Telegram client
- `getWhatsAppClient()` - Get singleton WhatsApp client
- `detectIntent()` - Recognize voice commands
- `routeToPlatform()` - Route intents to adapters

---

## 📚 Documentation Links

- **Detailed Setup**: [TELEGRAM_WHATSAPP_SETUP.md](TELEGRAM_WHATSAPP_SETUP.md)
- **Integration Overview**: [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)
- **Telegram API**: [core.telegram.org](https://core.telegram.org)
- **Telethon Docs**: [docs.telethon.dev](https://docs.telethon.dev)
- **Twilio Docs**: [twilio.com/docs](https://www.twilio.com/docs)

---

## 💡 Best Practices

1. **Load `.env` Early**: Initialize platforms during app startup
2. **Error Handling**: Always check `result.success` before using data
3. **Phone Numbers**: Always use international format with `+`
4. **Session Management**: Store Telegram sessions securely
5. **Rate Limiting**: Implement backoff for API calls
6. **Logging**: Use `console.log` for debugging (marked with `[TELEGRAM]`/`[WHATSAPP]`)

---

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Get API credentials
3. ✅ Set environment variables
4. ✅ Initialize platforms
5. ✅ Test with voice commands
6. 📝 Customize for your needs
7. 🚀 Deploy to production

---

**Version**: 1.0  
**Last Updated**: February 7, 2026  
**Status**: Production Ready
