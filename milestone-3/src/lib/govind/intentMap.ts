// src/lib/govind/intentMap.ts

export type IntentAction =
  | "READ"
  | "DRAFT"
  | "REPLY"
  | "SEND"
  | "SUMMARIZE"
  | "LOGIN"
  | "LOGOUT"
  | "REGISTER"
  | "OPEN_PLATFORM"
  | "VIEW_FOLDER"
  | "EXIT"
  | "UNKNOWN";

export type TargetPlatform = "gmail" | "outlook" | "telegram" | "system";

export interface ResolvedIntent {
  action: IntentAction;
  platform: TargetPlatform;
  text: string; // ✅ ADDED
  entities: {
    to?: string;
    subject?: string;
    body?: string;
    messageId?: string;
    query?: string;
  };
}

const intentPatterns: { action: IntentAction; platform: TargetPlatform; keywords: string[] }[] = [
  // Navigation (Specific first)
  { action: "OPEN_PLATFORM", platform: "gmail", keywords: ["open gmail", "go to gmail", "launch gmail"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open inbox", "go to inbox", "show inbox", "inbox"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open starred", "show starred", "starred", "favorites"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open sent", "show sent", "sent", "sent mail"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open drafts", "show drafts", "drafts"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open trash", "show trash", "trash", "deleted"] },
  { action: "VIEW_FOLDER", platform: "gmail", keywords: ["open spam", "show spam", "spam"] },

  // Telegram Navigation
  { action: "OPEN_PLATFORM", platform: "telegram", keywords: ["open telegram", "go to telegram", "launch telegram", "open tg", "show telegram"] },
  { action: "READ", platform: "telegram", keywords: ["read telegram", "check telegram", "telegram messages", "new telegram", "read my telegram", "check telegram messages", "read telegram chats", "show telegram messages", "any telegram messages"] },
  // Telegram messaging - must come before generic Gmail patterns
  { action: "SEND", platform: "telegram", keywords: ["open chat with", "open chat", "chat with", "send message to", "message to", "send telegram to", "telegram message to", "send telegram", "message on telegram", "telegram to", "message via telegram", "send telegram message", "compose telegram", "write telegram", "new telegram message"] },
  { action: "REPLY", platform: "telegram", keywords: ["reply on telegram", "respond on telegram", "reply to telegram", "answer telegram", "reply telegram message"] },
  { action: "SUMMARIZE", platform: "telegram", keywords: ["summarize telegram", "telegram summary", "what's in telegram", "telegram digest"] },

  // Gmail Actions
  { action: "READ", platform: "gmail", keywords: ["read", "check mail", "inbox", "new email", "what do i have", "open"] },
  { action: "SUMMARIZE", platform: "gmail", keywords: ["summarize", "summary", "digest", "what is it about"] },
  { action: "REPLY", platform: "gmail", keywords: ["reply", "respond", "answer"] },
  { action: "SEND", platform: "gmail", keywords: ["send", "compose", "write an email"] },

  // Auth
  { action: "LOGIN", platform: "system", keywords: ["login", "sign in", "log in"] },
  { action: "REGISTER", platform: "system", keywords: ["register", "sign up", "create account"] },
  { action: "LOGOUT", platform: "system", keywords: ["logout", "sign out"] },
  { action: "EXIT", platform: "system", keywords: ["exit", "stop", "close", "sleep"] },
];

/**
 * 🧠 3A. Intent Detection (STATELESS)
 * Classifies the transcript into an action and platform.
 */
export function detectIntent(text: string): ResolvedIntent {

  // Correction: fix common STT misrecognition of 'chat' as 'chart'
  let normalized = text.toLowerCase().trim();
  // Only replace 'chart' with 'chat' if it appears as a word (not in 'charting', etc.)
  normalized = normalized.replace(/\bchart\b/g, "chat");

  // 1. Check patterns
  for (const pattern of intentPatterns) {
    if (pattern.keywords.some(k => normalized.includes(k))) {
      const entities: any = {};

      if (pattern.action === "VIEW_FOLDER") {
        if (normalized.includes("starred")) entities.query = "starred";
        else if (normalized.includes("sent")) entities.query = "sent";
        else if (normalized.includes("draft")) entities.query = "drafts";
        else if (normalized.includes("trash")) entities.query = "trash";
        else if (normalized.includes("spam")) entities.query = "spam";
        else entities.query = "inbox";
      }

      // Extract recipient name for Telegram messages
      if (pattern.action === "SEND" && pattern.platform === "telegram") {
        // Patterns: "open chat with [name]", "chat with [name]", "send message to [name]", "message to [name]"
        const nameMatch = normalized.match(/(?:open chat with|chat with|send message to|message to|telegram to|send telegram to)\s+(.+?)(?:\s*$|\s+saying|\s+message)/i);
        if (nameMatch && nameMatch[1]) {
          entities.to = nameMatch[1].trim();
        }
      }

      return {
        action: pattern.action,
        platform: pattern.platform,
        text,
        entities
      };
    }
  }

  // 2. Fallback
  return {
    action: "UNKNOWN",
    platform: "system",
    text,
    entities: { query: text }
  };
}


