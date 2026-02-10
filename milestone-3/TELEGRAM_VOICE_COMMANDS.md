# 📢 Telegram Voice Commands Guide

This document describes all voice commands available for Telegram integration in the Voice-Based Email Messaging Assistant.

## 🎯 Overview

Telegram voice commands allow you to manage your Telegram conversations hands-free using natural voice interactions with Govind, your AI assistant.

---

## 🔐 Connection Commands

### Connect to Telegram
- **"Open Telegram"**
- **"Go to Telegram"**
- **"Launch Telegram"**
- **"Show Telegram"**

**Example:** "Hey Govind, open Telegram"

---

## 📨 Reading Messages & Chats

### Read Recent Chats
- **"Read Telegram"**
- **"Check Telegram"**
- **"Read Telegram chats"**
- **"Show Telegram messages"**
- **"Read my Telegram"**
- **"Check Telegram messages"**
- **"Any Telegram messages?"**

**Response:** Govind will list your recent chats with unread message counts.

**Example:** "Hey Govind, check Telegram"

**Sample Response:** "You have 5 Telegram chats. 1. Family Group, 3 unread. 2. Work Team, no unread messages. 3. John Smith, 1 unread..."

### Read Messages from Specific Chat
- **"Read messages from [chat name]"**
- **"Show me messages from [contact name]"**

**Note:** Currently requires selecting a chat from the UI. Future updates will support voice chat selection.

---

## ✍️ Sending Messages

### Send New Message
- **"Send Telegram message"**
- **"Message on Telegram"**
- **"Send Telegram to [contact]"**
- **"Compose Telegram"**
- **"Write Telegram"**
- **"New Telegram message"**

**Example:** "Hey Govind, send Telegram message"

**Flow:**
1. Govind asks: "Who would you like to message?"
2. You say the contact name or chat name
3. Govind asks: "What would you like to say?"
4. You dictate your message
5. Govind confirms and sends

### Reply to Message
- **"Reply on Telegram"**
- **"Respond on Telegram"**
- **"Reply to Telegram"**
- **"Answer Telegram message"**

**Example:** "Hey Govind, reply on Telegram"

---

## 📊 Summaries & Analytics

### Get Telegram Summary
- **"Summarize Telegram"**
- **"Telegram summary"**
- **"What's in Telegram?"**
- **"Telegram digest"**

**Response:** Provides overview of unread messages, active conversations, and top priority chats.

**Example:** "Hey Govind, summarize Telegram"

**Sample Response:** "Telegram summary: You have 10 total chats. 15 unread messages across 3 conversations. Most active: Family Group with 5 unread, Work Team with 7 unread, John Smith with 3 unread."

---

## 🎮 UI Navigation Commands

### Open Specific Features
- **"Open Telegram chats"** - View conversations list
- **"Show Telegram contacts"** - Display contact list
- **"Go to Telegram settings"** - Access settings (future feature)

---

## 🔄 Combined Commands

You can combine actions in natural language:

- **"Read my new Telegram messages"**
- **"Check Telegram and tell me if I have any unread"**
- **"Open Telegram and read my chats"**
- **"Send a Telegram message to John"**

---

## 💡 Tips for Best Results

### 1. **Wake Up Govind First**
Always start with the wake word: **"Hey Govind"** or click the microphone button.

### 2. **Speak Clearly**
Use natural speech but speak clearly for best recognition.

### 3. **Be Specific**
The more specific you are, the better:
- ✅ "Send Telegram message to Sarah"
- ❌ "Message someone"

### 4. **Use Full Names**
When mentioning contacts:
- ✅ "John Smith"
- ✅ "Family Group"

### 5. **Confirm Actions**
Govind will ask for confirmation before sending messages. Say "yes" or "send" to confirm.

---

## 🚀 Advanced Usage

### Context-Aware Commands
Once you're on the Telegram page, Govind understands context:

On Telegram page:
- **"Read this chat"** - Reads currently selected chat
- **"Send a message"** - Sends to current chat
- **"Refresh"** - Refreshes chat list

### Canceling Operations
- **"Cancel"**
- **"Stop"**
- **"Never mind"**
- **"Go back"**

---

## 🔧 Voice Command Flow Examples

### Example 1: Check Messages
```
You: "Hey Govind"
Govind: "Hello! How can I help?"
You: "Check my Telegram"
Govind: "You have 5 Telegram chats. Family Group, 3 unread. Work Team, 0 unread..."
```

### Example 2: Send Message
```
You: "Hey Govind, send a Telegram message"
Govind: "Opening Telegram. Who would you like to message?"
You: "John Smith"
Govind: "What would you like to say to John Smith?"
You: "Hey John, wanted to check on that project update"
Govind: "Message sent to John Smith"
```

### Example 3: Get Summary
```
You: "Hey Govind, summarize my Telegram"
Govind: "Telegram summary: You have 10 total chats. 15 unread messages across 3 conversations..."
```

---

## ⚙️ Configuration

### Setup Requirements
1. Telegram API credentials (API ID and API Hash from [my.telegram.org](https://my.telegram.org))
2. Phone number associated with Telegram account
3. Active internet connection

### Connection Flow
1. Say: "Open Telegram"
2. Govind navigates to Telegram page
3. Click "Connect" or say "Connect to Telegram"
4. Provide credentials via the connection dialog
5. Enter verification code from Telegram

---

## 🐛 Troubleshooting

### "Telegram is not connected"
- Ensure you've connected via the Telegram page
- Check your API credentials
- Verify backend is running on port 5001

### Commands Not Recognized
- Ensure microphone permissions are granted
- Speak clearly after the wake word
- Try alternative phrasings from the lists above

### Messages Not Sending
- Verify Telegram connection status
- Check recipient name spelling
- Ensure backend connection is active

---

## 🔮 Upcoming Features

- ✨ Voice-based chat selection
- ✨ Voice search for contacts
- ✨ Group chat management
- ✨ Media message support
- ✨ Scheduled messages
- ✨ Message reactions via voice
- ✨ Voice note recording and playback

---

## 📝 Notes

- All voice commands are processed locally in your browser
- Commands require active backend connection (Flask API on port 5001)
- Natural language variations of commands are supported
- Case-insensitive command matching

---

## 🆘 Support

For issues or feature requests:
1. Check this guide first
2. Review console logs (F12 → Console)
3. Verify backend is running
4. Check Telegram connection status

---

**Last Updated:** February 9, 2026
**Version:** 1.0.0
