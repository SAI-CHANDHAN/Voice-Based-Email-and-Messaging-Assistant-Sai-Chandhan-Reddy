// src/services/messagingPlatformService.ts

import { getTelegramClient } from "@/lib/telegram/telegramClient";
import { TelegramConfig } from "@/lib/telegram/telegramTypes";

/**
 * Messaging Platform Service
 * Manages initialization and lifecycle of Telegram client
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
   * Initialize platform from environment variables
   */
  async initializeFromEnv(): Promise<{
    telegram: boolean;
  }> {
    console.log('[SERVICE] ========================================');
    console.log('[SERVICE] Initializing from environment variables...');
    console.log('[SERVICE] ========================================');
    
    const results = {
      telegram: false
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
   * Show status of all platforms
   */
  getStatus(): {
    telegram: { available: boolean; status: string };
  } {
    return {
      telegram: {
        available: this.isTelegramAvailable(),
        status: this.isTelegramAvailable() ? "Connected" : "Not connected"
      }
    };
  }
}

export const messagingPlatformService = MessagingPlatformService.getInstance();
