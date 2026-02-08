// src/lib/whatsapp/whatsappTypes.ts

/**
 * WhatsApp message object
 */
export interface WhatsAppMessage {
  sid: string; // Message SID from Twilio
  body: string;
  from: string; // Phone number
  to: string; // Phone number
  dateCreated: Date;
  status: "queued" | "sending" | "sent" | "failed" | "received";
  numSegments?: number;
}

/**
 * WhatsApp contact object
 */
export interface WhatsAppContact {
  phoneNumber: string;
  displayName?: string;
  lastMessageDate?: Date;
}

/**
 * WhatsApp send result
 */
export interface WhatsAppSendResult {
  success: boolean;
  messageSid?: string;
  error?: string;
  cost?: string;
}

/**
 * WhatsApp configuration
 */
export interface WhatsAppConfig {
  accountSid: string;
  authToken: string;
  whatsappPhoneNumber: string; // Twilio WhatsApp sandbox or production number
  webhookUrl?: string;
}

/**
 * WhatsApp webhook payload
 */
export interface WhatsAppWebhookPayload {
  MessageSid: string;
  AccountSid: string;
  From: string;
  To: string;
  Body: string;
  NumMedia?: string;
  [key: string]: any;
}
