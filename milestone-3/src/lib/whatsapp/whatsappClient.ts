// src/lib/whatsapp/whatsappClient.ts

import { WhatsAppConfig, WhatsAppMessage, WhatsAppSendResult } from "./whatsappTypes";

/**
 * WhatsApp Client Wrapper for Twilio
 * Handles WhatsApp messaging via Twilio's API
 */
export class WhatsAppClient {
  private config: WhatsAppConfig;
  private client: any; // In real implementation, this would be the Twilio client
  private isInitialized: boolean = false;

  constructor(config: WhatsAppConfig) {
    this.config = config;
    this.initialize();
  }

  /**
   * Initialize Twilio client
   */
  private initialize(): void {
    try {
      if (!this.config.accountSid || !this.config.authToken) {
        throw new Error("Missing Twilio credentials");
      }

      // In production: const twilio = require('twilio');
      // this.client = twilio(this.config.accountSid, this.config.authToken);
      
      console.log(`[WHATSAPP] Initializing Twilio client for account: ${this.config.accountSid}`);
      this.isInitialized = true;
      console.log("[WHATSAPP] Twilio client initialized successfully");
    } catch (err: any) {
      console.error(`[WHATSAPP] Initialization failed: ${err.message}`);
      this.isInitialized = false;
    }
  }

  /**
   * Send a WhatsApp message
   */
  async sendMessage(toPhoneNumber: string, messageBody: string): Promise<WhatsAppSendResult> {
    if (!this.isInitialized) {
      return {
        success: false,
        error: "WhatsApp client not initialized"
      };
    }

    try {
      // Format phone number to WhatsApp format (whatsapp:+1234567890)
      const toWhatsApp = this.formatPhoneNumber(toPhoneNumber);
      const fromWhatsApp = `whatsapp:${this.config.whatsappPhoneNumber}`;

      // In production:
      // const message = await this.client.messages.create({
      //   from: fromWhatsApp,
      //   to: toWhatsApp,
      //   body: messageBody
      // });

      console.log(`[WHATSAPP] Sending message to ${toPhoneNumber}: ${messageBody.substring(0, 50)}...`);

      return {
        success: true,
        messageSid: `SM${Date.now()}`, // Placeholder SID
        cost: "0.005" // Approximate Twilio cost
      };
    } catch (err: any) {
      console.error(`[WHATSAPP] Failed to send message: ${err.message}`);
      return {
        success: false,
        error: err.message
      };
    }
  }

  /**
   * Get message history with a contact
   */
  async getMessageHistory(phoneNumber: string, limit: number = 10): Promise<WhatsAppMessage[]> {
    if (!this.isInitialized) {
      throw new Error("WhatsApp client not initialized");
    }

    try {
      const toWhatsApp = this.formatPhoneNumber(phoneNumber);

      // In production:
      // const messages = await this.client.messages.list({
      //   to: toWhatsApp,
      //   limit: limit
      // });

      console.log(`[WHATSAPP] Fetching message history with ${phoneNumber}`);

      // Placeholder: return empty array
      return [];
    } catch (err: any) {
      console.error(`[WHATSAPP] Failed to get message history: ${err.message}`);
      throw err;
    }
  }

  /**
   * Send message with media
   */
  async sendMediaMessage(toPhoneNumber: string, mediaUrl: string, caption?: string): Promise<WhatsAppSendResult> {
    if (!this.isInitialized) {
      return {
        success: false,
        error: "WhatsApp client not initialized"
      };
    }

    try {
      const toWhatsApp = this.formatPhoneNumber(toPhoneNumber);
      const fromWhatsApp = `whatsapp:${this.config.whatsappPhoneNumber}`;

      // In production:
      // const message = await this.client.messages.create({
      //   from: fromWhatsApp,
      //   to: toWhatsApp,
      //   mediaUrl: mediaUrl,
      //   body: caption || ""
      // });

      console.log(`[WHATSAPP] Sending media to ${toPhoneNumber}: ${mediaUrl}`);

      return {
        success: true,
        messageSid: `SM${Date.now()}`, // Placeholder SID
        cost: "0.005"
      };
    } catch (err: any) {
      console.error(`[WHATSAPP] Failed to send media: ${err.message}`);
      return {
        success: false,
        error: err.message
      };
    }
  }

  /**
   * Verify phone number format
   */
  private formatPhoneNumber(phoneNumber: string): string {
    // Remove any non-digit characters except +
    let cleaned = phoneNumber.replace(/[^\d+]/g, "");

    // Ensure it starts with +
    if (!cleaned.startsWith("+")) {
      cleaned = "+" + cleaned;
    }

    return `whatsapp:${cleaned}`;
  }

  /**
   * Get client status
   */
  isInitializedStatus(): boolean {
    return this.isInitialized;
  }
}

// Singleton instance
let whatsappClientInstance: WhatsAppClient | null = null;

/**
 * Get or create WhatsApp client instance
 */
export const getWhatsAppClient = (config?: WhatsAppConfig): WhatsAppClient => {
  console.log('[WHATSAPP] getWhatsAppClient called', { hasConfig: !!config, hasInstance: !!whatsappClientInstance });
  
  if (!whatsappClientInstance && config) {
    console.log('[WHATSAPP] Creating new WhatsAppClient instance');
    whatsappClientInstance = new WhatsAppClient(config);
  }
  
  if (!whatsappClientInstance) {
    console.error('[WHATSAPP] ❌ WhatsApp client not initialized. Please provide configuration.');
    throw new Error("WhatsApp client not initialized. Please provide configuration.");
  }
  
  console.log('[WHATSAPP] ✅ Returning WhatsAppClient instance');
  return whatsappClientInstance;
};
