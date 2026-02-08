// src/App.tsx

import { useEffect, useRef } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { GovindProvider, useGovind } from "@/contexts/GovindContext";
import { GmailProvider } from "@/contexts/GmailContext";
import { auth } from "@/lib/firebase/firebase";
import {
  initVoiceRecognition,
  startListening,
} from "@/lib/govind/voiceStateController";
import { initPlatforms } from "@/lib/platforms/init";
import { bindVoiceLifecycle } from "@/lib/govind/voiceLifecycle";
import { messagingPlatformService } from "@/services/messagingPlatformService";

// Pages
import Index from "./pages/Index";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Gmail from "./pages/Gmail";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Docs from "./pages/Docs";
import { Outlook, Telegram, WhatsApp } from "./pages/Platforms";
import NotFound from "./pages/NotFound";
import GmailOAuth from "./pages/GmailOAuth";

/* ======================================================
   🔍 FIREBASE AUTH DEBUG (SAFE)
   ====================================================== */

auth.onAuthStateChanged((user) => {
  console.log("[FIREBASE AUTH]", user ? user.email : "NOT LOGGED IN");
});

const queryClient = new QueryClient();

/* ======================================================
   🚀 PLATFORM INITIALIZATION
   ====================================================== */

console.log('========================================');
console.log('🚀 Govind App Initializing...');
console.log('========================================');

// Initialize all platform adapters (Gmail, Telegram, WhatsApp)
initPlatforms();

// Initialize messaging platforms from environment
messagingPlatformService.initializeFromEnv().then((status) => {
  console.log('[APP] Platform initialization complete:', status);
  if (status.telegram) console.log('[APP] ✅ Telegram ready');
  if (status.whatsapp) console.log('[APP] ✅ WhatsApp ready');
}).catch((err) => {
  console.error('[APP] Platform initialization error:', err);
});

console.log('========================================');

/* ======================================================
   🎙️ VOICE BOOTSTRAP (SINGLE ENTRY POINT)
   ====================================================== */

const VoiceBootstrap = () => {
  const { state, wakeUp, handleIntent } = useGovind();

  const recognitionRef = useRef<any>(null);
  const stateRef = useRef(state);

  // Keep latest state
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.error("[VOICE] SpeechRecognition not supported");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognitionRef.current = recognition;

    // Init mic controller
    initVoiceRecognition(recognition);

    // Bind voice → Govind pipeline
    bindVoiceLifecycle(
      recognition,
      () => stateRef.current,
      (text: string) => {
        // Core transcript handling is now done via govind:voice_event
        // listeners in GovindContext.tsx to ensure single-dispatch and correct state.
        console.log("[VOICE] Lifecycle transcript:", text);
      },
      () => {
        console.log("[VOICE] Reset requested");
      }
    );

    console.log("[VOICE] Ready — waiting for user gesture");
  }, []);

  return null;
};

/* ======================================================
   🚀 APP ROOT
   ====================================================== */
const RouteDebugger = () => {
  const location = useLocation();

  useEffect(() => {
    console.log("[ROUTE DEBUG] Current path:", location.pathname);
  }, [location.pathname]);

  return null;
};

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>

          {/* 🔐 Gmail must wrap Govind */}
          <GmailProvider>
            <GovindProvider>

              {/* 🎙️ VOICE SYSTEM (GLOBAL, ONCE) */}
              <VoiceBootstrap />

              {/* 🌐 ROUTER */}
              <Routes>
                {/* Public */}
                <Route path="/" element={<Index />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Core */}
                <Route path="/dashboard" element={<Dashboard />} />

                {/* Platforms */}
                <Route path="/gmail-oauth" element={<GmailOAuth />} />
                <Route path="/gmail" element={<Gmail />} />
                <Route path="/outlook" element={<Outlook />} />
                <Route path="/telegram" element={<Telegram />} />
                <Route path="/whatsapp" element={<WhatsApp />} />

                {/* User */}
                <Route path="/profile" element={<Profile />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/docs" element={<Docs />} />

                {/* Fallback */}
                <Route path="*" element={<NotFound />} />
              </Routes>

              {/* 🔔 GLOBAL UI */}
              <Toaster />
              <Sonner />

            </GovindProvider>
          </GmailProvider>

        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};


export default App;
