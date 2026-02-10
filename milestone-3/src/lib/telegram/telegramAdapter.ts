// src/lib/telegram/telegramAdapter.ts

import { PlatformAdapter, ExecutionResult } from "@/lib/platforms/platformTypes";
import { ResolvedIntent } from "@/lib/govind/intentMap";
import { getTelegramClient } from "./telegramClient";

/**
 * Telegram Platform Adapter
 * Implements voice-based messaging for Telegram
 */
export const TelegramAdapter: PlatformAdapter = {
  id: "telegram",
  name: "Telegram Messenger",

  execute: async (intent: ResolvedIntent): Promise<ExecutionResult> => {
    const text = intent.text.toLowerCase();

    try {
      // Initialize Telegram client
      const client = getTelegramClient();

      if (!client.isConnectedStatus()) {
        return {
          success: false,
          message: "Telegram is not connected. Please authenticate first.",
          error: "TELEGRAM_NOT_CONNECTED"
        };
      }

      switch (intent.action) {
        case "READ": {
          // Read recent messages or chats
          try {
            // Check if asking for chats overview or specific chat messages
            const wantsChats = text.includes("chats") || text.includes("conversations") || !text.includes("from") && !text.includes("message");
            
            if (wantsChats) {
              // List recent chats
              const chats = await client.getChats(10);
              
              if (chats.length === 0) {
                return {
                  success: true,
                  message: "You have no recent Telegram chats."
                };
              }
              
              let spokenText = `You have ${chats.length} Telegram chats. `;
              const topChats = chats.slice(0, 5);
              topChats.forEach((chat, idx) => {
                const unread = chat.unreadCount > 0 ? `, ${chat.unreadCount} unread` : "";
                spokenText += `${idx + 1}. ${chat.title}${unread}. `;
              });
              
              return {
                success: true,
                message: spokenText,
                data: { chats, type: "CHATS_LIST" }
              };
            }
            
            // Parse chat or user identifier from text
            const chatIdMatch = text.match(/chat[\s:]*(\d+)|from[\s:]*([a-z0-9_]+)/i);
            const chatId = chatIdMatch ? parseInt(chatIdMatch[1]) : -1;

            if (chatId === -1) {
              return {
                success: true,
                message: "Which chat would you like to read messages from? Please specify a contact or chat name."
              };
            }

            const messages = await client.getMessages(chatId, 5);

            if (messages.length === 0) {
              return {
                success: true,
                message: `No messages found in this chat.`
              };
            }

            // Format messages for voice
            let spokenText = `You have ${messages.length} messages. `;
            messages.slice(0, 3).forEach((msg, idx) => {
              spokenText += `Message ${idx + 1} from ${msg.senderName || "Unknown"}: ${msg.text.substring(0, 100)}. `;
            });

            return {
              success: true,
              message: spokenText,
              data: { messages, type: "MESSAGES_LIST" }
            };
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to read Telegram messages",
              error: err.message
            };
          }
        }

        case "SEND": {
          // Send a new message
          try {
            const toMatch = text.match(/to\s+([a-z0-9_]+)|message\s+([a-z0-9_]+)/i);
            const bodyMatch = text.match(/message:\s*(.+?)(?:\.|$)|body:\s*(.+?)(?:\.|$)/i);

            const recipient = toMatch ? (toMatch[1] || toMatch[2]) : intent.entities.to;
            const body = bodyMatch ? (bodyMatch[1] || bodyMatch[2]) : intent.entities.body;

            if (!recipient || !body) {
              return {
                success: false,
                message: "Please specify both the recipient and the message content.",
                error: "MISSING_FIELDS"
              };
            }

            // In real implementation, would resolve contact name to chat ID
            const chatId = -1; // Placeholder

            const result = await client.sendMessage(chatId, body);

            if (result.success) {
              return {
                success: true,
                message: `Message sent to ${recipient}. Your message: "${body}"`
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
            const messageIdMatch = text.match(/message[\s:]*(\d+)|reply.*?id[\s:]*(\d+)/i);
            const bodyMatch = text.match(/with:\s*(.+?)(?:\.|$)|say:\s*(.+?)(?:\.|$)|reply:\s*(.+?)(?:\.|$)/i);

            const messageId = messageIdMatch ? parseInt(messageIdMatch[1] || messageIdMatch[2]) : -1;
            const replyBody = bodyMatch ? (bodyMatch[1] || bodyMatch[2] || bodyMatch[3]) : intent.entities.body;

            if (messageId === -1 || !replyBody) {
              return {
                success: false,
                message: "Please specify which message to reply to and what you want to say.",
                error: "MISSING_FIELDS"
              };
            }

            // In real implementation, would get chat ID from message context
            const chatId = -1; // Placeholder

            const result = await client.replyToMessage(chatId, messageId, replyBody);

            if (result.success) {
              return {
                success: true,
                message: `Reply sent: "${replyBody}"`
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
              message: "Failed to reply to message",
              error: err.message
            };
          }
        }

        case "OPEN_PLATFORM": {
          // Open/Connect to Telegram
          try {
            if (!client.isConnectedStatus()) {
              // In production, would initiate connection flow
              return {
                success: true,
                message: "Opening Telegram. Please authenticate with your phone number."
              };
            }
            const userInfo = await client.getUserInfo();
            return {
              success: true,
              message: `Welcome back, ${userInfo?.firstName || "User"}! Telegram is ready.`
            };
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to open Telegram",
              error: err.message
            };
          }
        }

        case "SUMMARIZE": {
          // Summarize recent Telegram activity
          try {
            const chats = await client.getChats(10);
            
            if (chats.length === 0) {
              return {
                success: true,
                message: "You have no Telegram chats to summarize."
              };
            }
            
            const totalUnread = chats.reduce((sum, chat) => sum + (chat.unreadCount || 0), 0);
            const activeChats = chats.filter(chat => chat.unreadCount && chat.unreadCount > 0).length;
            
            let summary = `Telegram summary: You have ${chats.length} total chats. `;
            
            if (totalUnread > 0) {
              summary += `${totalUnread} unread messages across ${activeChats} conversations. `;
              
              // List top 3 chats with unread messages
              const unreadChats = chats.filter(c => c.unreadCount && c.unreadCount > 0).slice(0, 3);
              if (unreadChats.length > 0) {
                summary += "Most active: ";
                unreadChats.forEach((chat, idx) => {
                  summary += `${chat.title} with ${chat.unreadCount} unread${idx < unreadChats.length - 1 ? ", " : ". "}`;
                });
              }
            } else {
              summary += "All chats are up to date. ";
            }
            
            return {
              success: true,
              message: summary,
              data: { chats, totalUnread, activeChats }
            };
          } catch (err: any) {
            return {
              success: false,
              message: "Failed to summarize Telegram activity",
              error: err.message
            };
          }
        }

        default: {
          return {
            success: false,
            message: `Action "${intent.action}" not supported on Telegram yet.`,
            error: "ACTION_NOT_SUPPORTED"
          };
        }
      }
    } catch (err: any) {
      return {
        success: false,
        message: "An error occurred while processing your Telegram request",
        error: err?.message || "UNKNOWN_ERROR"
      };
    }
  }
};
