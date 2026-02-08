// src/services/messagingPlatformService.ts

import { getTelegramClient } from "@/lib/telegram/telegramClient";
import { getWhatsAppClient } from "@/lib/whatsapp/whatsappClient";
import { TelegramConfig } from "@/lib/telegram/telegramTypes";
import { WhatsAppConfig } from "@/lib/whatsapp/whatsappTypes";

/**
 * Messaging Platform Service
 * Manages initialization and lifecycle of Telegram and WhatsApp clients
 */
export class MessagingPlatformService {
  private static instance: MessagingPlatformService;

  private constructor() {}

  /**
   * Get singleton instance
   */
  static getInstance(): MessagingPlatformService {
    if (!this.instance) {
      this.instance = new MessagingPlatformService();
    }
    return this.instance;
  }

  /**
   * Initialize Telegram client with configuration
   */
  async initializeTelegram(config: TelegramConfig): Promise<boolean> {
    try {
      const client = getTelegramClient(config);
      await client.connect();
      console.log("[SERVICE] Telegram initialized successfully");
      return true;
    } catch (err: any) {
      console.error("[SERVICE] Failed to initialize Telegram:", err.message);
      return false;
    }
  }

  /**
   * Initialize WhatsApp client with configuration
   */
  async initializeWhatsApp(config: WhatsAppConfig): Promise<boolean> {
    try {
      const client = getWhatsAppClient(config);
      console.log("[SERVICE] WhatsApp initialized successfully");
      return true;
    } catch (err: any) {
      console.error("[SERVICE] Failed to initialize WhatsApp:", err.message);
      return false;
    }
  }

  /**
   * Initialize both platforms from environment variables
   */
  async initializeFromEnv(): Promise<{
    telegram: boolean;
    whatsapp: boolean;
  }> {
    console.log('[SERVICE] ========================================');
    console.log('[SERVICE] Initializing from environment variables...');
    console.log('[SERVICE] ========================================');
    
    const results = {
      telegram: false,
      whatsapp: false
    };

    // Initialize Telegram
    const telegramApiId = import.meta.env.VITE_TELEGRAM_API_ID;
    const telegramApiHash = import.meta.env.VITE_TELEGRAM_API_HASH;
    
    console.log('[TELEGRAM] API ID available:', !!telegramApiId);
    console.log('[TELEGRAM] API Hash available:', !!telegramApiHash);
    
    if (telegramApiId && telegramApiHash) {
      console.log('[TELEGRAM] 🔄 Attempting initialization...');
      results.telegram = await this.initializeTelegram({
        apiId: parseInt(telegramApiId),
        apiHash: telegramApiHash,
        phoneNumber: import.meta.env.VITE_TELEGRAM_PHONE_NUMBER,
        sessionName: import.meta.env.VITE_TELEGRAM_SESSION_NAME || "session"
      });
      console.log('[TELEGRAM] ✅ Status:', results.telegram);
    } else {
      console.log('[TELEGRAM] ⚠️ Missing credentials in environment');
    }

    // Initialize WhatsApp
    const twiliSid = import.meta.env.VITE_TWILIO_ACCOUNT_SID;
    const twilioToken = import.meta.env.VITE_TWILIO_AUTH_TOKEN;
    
    console.log('[WHATSAPP] Account SID available:', !!twiliSid);
    console.log('[WHATSAPP] Auth Token available:', !!twilioToken);
    
    if (twiliSid && twilioToken) {
      console.log('[WHATSAPP] 🔄 Attempting initialization...');
      results.whatsapp = await this.initializeWhatsApp({
        accountSid: twiliSid,
        authToken: twilioToken,
        whatsappPhoneNumber: import.meta.env.VITE_TWILIO_WHATSAPP_PHONE_NUMBER,
        webhookUrl: import.meta.env.VITE_TWILIO_WEBHOOK_URL
      });
      console.log('[WHATSAPP] ✅ Status:', results.whatsapp);
    } else {
      console.log('[WHATSAPP] ⚠️ Missing credentials in environment');
    }

    console.log('[SERVICE] ========================================');
    console.log('[SERVICE] Initialization Results:', results);
    console.log('[SERVICE] ========================================');
    
    return results;
  }

  /**
   * Get Telegram client
   */
  getTelegramClient() {
    return getTelegramClient();
  }

  /**
   * Get WhatsApp client
   */
  getWhatsAppClient() {
    return getWhatsAppClient();
  }

  /**
   * Check if Telegram is available
   */
  isTelegramAvailable(): boolean {
    try {
      const client = getTelegramClient();
      return client.isConnectedStatus();
    } catch {
      return false;
    }
  }

  /**
   * Check if WhatsApp is available
   */
  isWhatsAppAvailable(): boolean {
    try {
      const client = getWhatsAppClient();
      return client.isInitializedStatus();
    } catch {
      return false;
    }
  }

  /**
   * Show status of all platforms
   */
  getStatus(): {
    telegram: { available: boolean; status: string };
    whatsapp: { available: boolean; status: string };
  } {
    return {
      telegram: {
        available: this.isTelegramAvailable(),
        status: this.isTelegramAvailable() ? "Connected" : "Not connected"
      },
      whatsapp: {
        available: this.isWhatsAppAvailable(),
        status: this.isWhatsAppAvailable() ? "Initialized" : "Not initialized"
      }
    };
  }
}

export const messagingPlatformService = MessagingPlatformService.getInstance();
