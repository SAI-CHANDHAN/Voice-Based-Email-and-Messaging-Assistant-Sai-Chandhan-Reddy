// src/lib/telegram/telegramTypes.ts

/**
 * Telegram message object
 */
export interface TelegramMessage {
  id: number;
  senderId: number;
  text: string;
  date: Date;
  chatId: number;
  senderName?: string;
  isReply?: boolean;
  replyToId?: number;
  fromSelf?: boolean;
}

/**
 * Telegram chat object
 */
export interface TelegramChat {
  id: number;
  title?: string;
  isPrivate: boolean;
  isSupergroup: boolean;
  participantsCount?: number;
  unreadCount?: number;
  lastMessage?: string;
}

/**
 * Telegram send result
 */
export interface TelegramSendResult {
  success: boolean;
  messageId?: number;
  error?: string;
}

/**
 * Telegram connection config
 */
export interface TelegramConfig {
  apiId: number;
  apiHash: string;
  phoneNumber?: string;
  sessionName?: string;
}

/**
 * Telegram user details
 */
export interface TelegramUser {
  id: number;
  firstName: string;
  lastName?: string;
  username?: string;
  phoneNumber?: string;
}
