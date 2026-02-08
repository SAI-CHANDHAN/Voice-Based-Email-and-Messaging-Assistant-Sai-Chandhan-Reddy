// src/lib/platforms/init.ts

import { registerPlatform } from "./platformRegistry";
import { GmailAdapter } from "@/lib/google/gmailAdapter";
import { TelegramAdapter } from "@/lib/telegram/telegramAdapter";
import { WhatsAppAdapter } from "@/lib/whatsapp/whatsappAdapter";

/**
 * Initialize all platform adapters
 */
export const initPlatforms = () => {
    console.log('[INIT] Starting platform registration...');
    
    console.log('[INIT] Registering Gmail adapter...');
    registerPlatform(GmailAdapter);
    console.log('[INIT] ✅ Gmail adapter registered');
    
    console.log('[INIT] Registering Telegram adapter...');
    registerPlatform(TelegramAdapter);
    console.log('[INIT] ✅ Telegram adapter registered');
    
    console.log('[INIT] Registering WhatsApp adapter...');
    registerPlatform(WhatsAppAdapter);
    console.log('[INIT] ✅ WhatsApp adapter registered');

    console.log('[INIT] 🎉 All platforms initialized successfully!');
    // OutlookAdapter and other adapters can be added here in future stages
};
