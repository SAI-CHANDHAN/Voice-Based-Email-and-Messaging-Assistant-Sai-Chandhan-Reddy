// src/lib/whatsapp/whatsappAdapter.ts

import { PlatformAdapter, ExecutionResult } from "@/lib/platforms/platformTypes";
import { ResolvedIntent } from "@/lib/govind/intentMap";
import { getWhatsAppClient } from "./whatsappClient";

/**
 * WhatsApp Platform Adapter
 * Implements voice-based messaging for WhatsApp via Twilio
 */
export const WhatsAppAdapter: PlatformAdapter = {
  id: "whatsapp",
  name: "WhatsApp Messenger",

  execute: async (intent: ResolvedIntent): Promise<ExecutionResult> => {
    const text = intent.text.toLowerCase();

    try {
      // Initialize WhatsApp client
      const client = getWhatsAppClient();

      if (!client.isInitializedStatus()) {
        return {
          success: false,
          message: "WhatsApp is not initialized. Please configure Twilio credentials.",
          error: "WHATSAPP_NOT_INITIALIZED"
        };
      }

      switch (intent.action) {
        case "READ": {
          // Read messages from a contact
          try {
            // Parse phone number or contact from text
            const phoneMatch = text.match(/\+?[\d\s\-()]{10,}/);
            const phoneNumber = phoneMatch ? phoneMatch[0] : intent.entities.to;

            if (!phoneNumber) {
              return {
                success: true,
                message: "Which contact would you like to read messages from? Please provide a phone number or contact name."
              };
            }

            const messages = await client.getMessageHistory(phoneNumber, 5);

            if (messages.length === 0) {
              return {
                success: true,
                message: `No messages found with ${phoneNumber}.`
              };
            }

            // Format messages for voice
            let spokenText = `You have ${messages.length} messages from ${phoneNumber}. `;
            messages.slice(0, 3).forEach((msg, idx) => {
              const senderLabel = msg.from === phoneNumber ? "They said" : "You said";
              spokenText += `${senderLabel}: ${msg.body.substring(0, 100)}. `;
            });

            return {
              success: true,
              message: spokenText,
              data: { messages, type: "MESSAGES_LIST" }
            };
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to read messages",
              error: err.message
            };
          }
        }

        case "SEND": {
          // Send a new message
          try {
            const phoneMatch = text.match(/\+?[\d\s\-()]{10,}/);
            const phoneNumber = phoneMatch ? phoneMatch[0] : intent.entities.to;
            const body = intent.entities.body;

            if (!phoneNumber || !body) {
              return {
                success: false,
                message: "Please specify both the phone number and the message content.",
                error: "MISSING_FIELDS"
              };
            }

            const result = await client.sendMessage(phoneNumber, body);

            if (result.success) {
              return {
                success: true,
                message: `Message sent to ${phoneNumber}. Your message: "${body}". Message SID: ${result.messageSid}`
              };
            } else {
              return {
                success: false,
                message: "Failed to send message",
                error: result.error
              };
            }
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to send message",
              error: err.message
            };
          }
        }

        case "REPLY": {
          // Reply to a message
          try {
            const phoneMatch = text.match(/\+?[\d\s\-()]{10,}/);
            const phoneNumber = phoneMatch ? phoneMatch[0] : intent.entities.to;
            const replyBody = intent.entities.body;

            if (!phoneNumber || !replyBody) {
              return {
                success: false,
                message: "Please specify the phone number and what you want to reply.",
                error: "MISSING_FIELDS"
              };
            }

            const result = await client.sendMessage(phoneNumber, replyBody);

            if (result.success) {
              return {
                success: true,
                message: `Reply sent to ${phoneNumber}: "${replyBody}"`
              };
            } else {
              return {
                success: false,
                message: "Failed to send reply",
                error: result.error
              };
            }
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to reply",
              error: err.message
            };
          }
        }

        case "OPEN_PLATFORM": {
          // Open/Initialize WhatsApp
          return {
            success: true,
            message: "WhatsApp is ready to use. You can now send and receive messages."
          };
        }

        case "DRAFT": {
          // Compose a draft message
          try {
            const phoneMatch = text.match(/\+?[\d\s\-()]{10,}/);
            const phoneNumber = phoneMatch ? phoneMatch[0] : intent.entities.to;
            const body = intent.entities.body;

            if (!phoneNumber || !body) {
              return {
                success: false,
                message: "Please provide both the phone number and message content.",
                error: "MISSING_FIELDS"
              };
            }

            return {
              success: true,
              message: `Draft created for ${phoneNumber}. Message: "${body}". Say 'send' when ready.`,
              data: { phoneNumber, body, type: "DRAFT" }
            };
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to create draft",
              error: err.message
            };
          }
        }

        case "SUMMARIZE": {
          // Summarize conversation (future feature)
          return {
            success: true,
            message: "Conversation summarization for WhatsApp will be available soon."
          };
        }

        default: {
          return {
            success: false,
            message: `Action "${intent.action}" not supported on WhatsApp yet.`,
            error: "ACTION_NOT_SUPPORTED"
          };
        }
      }
    } catch (err: any) {
      return {
        success: false,
        message: "An error occurred while processing your WhatsApp request",
        error: err?.message || "UNKNOWN_ERROR"
      };
    }
  }
};
