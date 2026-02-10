//src/contexts/GovindContext.tsx

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";

import { detectIntent } from "@/lib/govind/intentMap";
import { useGmail } from "@/contexts/GmailContext";
import { useTelegram } from "@/contexts/TelegramContext";
import { onAuthChange } from "@/lib/firebase/auth";
import { speakText } from "@/services/ttsService";
import type { GovindState } from "@/lib/govind/stateMachine";
import { handleGlobalCommand } from "@/lib/govind/commandRouter";
import { completeRegistration } from "@/services/registrationFlow";
import { loginStep1BaseAuth, loginStep2Finalize } from "@/services/loginFlow";
import { User } from "firebase/auth";
import {
  canAcceptVoice,
} from "@/lib/govind/stateMachine";
import { useNavigate } from "react-router-dom";
import { interruptTTS } from "@/services/ttsService";
import { resetVoiceController } from "@/lib/govind/voiceStateController";
import {
  restoreSession,
  createSession,
  destroySession,
} from "@/lib/identity/sessionManager";
import { pauseListening } from "@/lib/govind/voiceStateController";
import { VoiceEvent } from "@/voice/voiceTypes";
import {
  handleRegisterSpeech,
  handleLoginSpeech,
  RegistrationSession,
} from "@/auth/authController";
import { generateEmailDraft } from "@/services/emailDrafter";
import { RegisterStep, LoginStep } from "@/auth/authTypes";
import { hashVoicePin } from "@/services/voicePinService";
import {
  createUserProfile,
  updateVoicePinHash,
  markFaceRegistered,
  getSecurityStateByEmail,
} from "@/lib/firebase/users";
import { getFaceImageUrl } from "@/lib/firebase/storage";
import { routeToPlatform } from "@/lib/platforms/platformRouter";





/* ================= TYPES ================= */

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

type AuthMode = "LOGIN" | "REGISTER" | null;

type AuthStep =
  | "IDLE"
  | RegisterStep
  | LoginStep
  | "COMPLETE";

interface GovindContextType {

  setRegistrationEmail: (email: string) => void;
  setRegistrationPassword: (password: string) => void;
  setRegistrationVoicePinHash: (hash: string) => void;
  setRegistrationFaceImage: (file: File) => void;
  setLoginEmail: (email: string) => void;
  setLoginPassword: (password: string) => void;
  setLoginSpokenPin: (pin: string) => void;
  handleIntent: (text: string) => void;


  state: GovindState;
  messages: Message[];
  isAssistantOpen: boolean;
  setIsAssistantOpen: (v: boolean) => void;
  assistantEnabled: boolean;
  enableAssistant: () => Promise<void>;

  speak: (text: string) => void;
  addMessage: (role: Message["role"], content: string) => void;
  setState: React.Dispatch<React.SetStateAction<GovindState>>;
  wakeUp: () => void;

  authMode: AuthMode;
  authStep: AuthStep;
  setAuthStep: (s: AuthStep) => void;

  isAuthenticated: boolean;
  setIsAuthenticated: (v: boolean) => void;
  userName: string | null;
  setUserName: (n: string | null) => void;

  routeIntent: string | null;
  setRouteIntent: (s: string | null) => void;

  faceImageUrl: string | null;
}



const GovindContext = createContext<GovindContextType | undefined>(undefined);


export const useGovind = () => {
  const ctx = useContext(GovindContext);
  if (!ctx) throw new Error("GovindContext missing");
  return ctx;
};


/* ================= PROVIDER ================= */

export const GovindProvider = ({ children }: { children: ReactNode }) => {

  const navigate = useNavigate();
  const [state, setState] = useState<GovindState>("DORMANT");

  const [messages, setMessages] = useState<Message[]>([]);
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);
  const openAssistant = () => setIsAssistantOpen(true);
  const closeAssistant = () => setIsAssistantOpen(false);
  const [assistantEnabled, setAssistantEnabled] = useState(false);
  // 🔹 Voice routing mode (GLOBAL = default, GMAIL = Gmail commands, COMPOSE_FLOW = Gmail compose, TELEGRAM_COMPOSE_FLOW = Telegram compose)
  const [voiceMode, setVoiceMode] = useState<"GLOBAL" | "GMAIL" | "COMPOSE_FLOW" | "TELEGRAM_COMPOSE_FLOW">("GLOBAL");

  const [authMode, setAuthMode] = useState<AuthMode>(null);
  const [authStep, setAuthStep] = useState<AuthStep>("IDLE");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [routeIntent, setRouteIntent] =
    useState<string | null>(null);
  const [faceImageUrl, setFaceImageUrl] = useState<string | null>(null);

  // 📝 Compose State (Voice Flow)
  const [composeStep, setComposeStep] = useState<"IDLE" | "TO" | "CONFIRM_TO" | "PROMPT" | "CONFIRM_DRAFT" | "CONFIRM_SEND">("IDLE");
  const composeStepRef = useRef(composeStep);
  const composeDataRef = useRef({ to: '', subject: '', body: '' });

  // 📱 Telegram Compose State (Voice Flow)
  const [telegramComposeStep, setTelegramComposeStep] = useState<"IDLE" | "TO" | "CONFIRM_TO" | "MESSAGE" | "CONFIRM_SEND">("IDLE");
  const telegramComposeStepRef = useRef(telegramComposeStep);
  const telegramComposeDataRef = useRef({ to: '', chatId: null as number | null, message: '' });

  useEffect(() => {
    composeStepRef.current = composeStep;
  }, [composeStep]);

  useEffect(() => {
    telegramComposeStepRef.current = telegramComposeStep;
  }, [telegramComposeStep]);



  const registrationDataRef = useRef<{
    email?: string;
    password?: string;
    voicePinHash?: string;
    faceImage?: File;
  }>({});
  const loginDataRef = useRef<{
    email?: string;
    password?: string;
    spokenPin?: string;
  }>({});
  const userRef = useRef<User | null>(null);
  const registrationConfirmRef = useRef<{
    password?: string;
    appPassword?: string;
  }>({});

  const setRegistrationEmail = (email: string) => {
    registrationDataRef.current.email = email;
  };

  const setRegistrationPassword = (password: string) => {
    registrationDataRef.current.password = password;
  };

  const setRegistrationVoicePinHash = (hash: string) => {
    registrationDataRef.current.voicePinHash = hash;
  };

  const setRegistrationFaceImage = (file: File) => {
    registrationDataRef.current.faceImage = file;
  };

  const setLoginEmail = (email: string) => {
    loginDataRef.current.email = email;
  };

  const setLoginPassword = (password: string) => {
    loginDataRef.current.password = password;
  };

  const setLoginSpokenPin = (pin: string) => {
    loginDataRef.current.spokenPin = pin;
  };


  const isAwakeRef = useRef(false);
  // 🔹 Gmail actions for voice control
  // 🔹 Gmail context (guarded to prevent crash if provider not mounted)
  const gmail = useGmail();
  const telegram = useTelegram();

  // ✅ Prevent stale state in async callbacks
  const authStepRef = useRef<AuthStep>("IDLE");
  const authModeRef = useRef<AuthMode>(null);
  const voiceModeRef = useRef(voiceMode);
  const stateRef = useRef<GovindState>("DORMANT");

  useEffect(() => {
    authStepRef.current = authStep;
    authModeRef.current = authMode;
    stateRef.current = state;
    voiceModeRef.current = voiceMode;
    composeDataRef.current = gmail.composeData;
  }, [authStep, authMode, state, voiceMode, gmail.composeData]);

  useEffect(() => {
    if (routeIntent) {
      console.log("[ROUTE] Navigating to", routeIntent);
      navigate(routeIntent);
    }
  }, [routeIntent]);
  // ✅ System Reset (Global State Recovery)
  const resetSystem = () => {
    console.log("[SYSTEM] Resetting all states");
    destroySession();
    pauseListening("GLOBAL_EXIT");  // 🔥 Stage-1: kill mic + pause reasons
    setAuthMode(null);
    setAuthStep("IDLE");
    setVoiceMode("GLOBAL");
    setState("SLEEPING");
    setIsAssistantOpen(false);
    isAwakeRef.current = false;
  };


  // ======================================================
  // 🔐 STAGE-2: ROUTE VOICE-AUTH → REAL INTENT PIPELINE

  // ======================================================
  useEffect(() => {
    const authHandler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!detail || detail.source !== "voice-auth") return;

      const intent = detail.text;
      if (!intent) return;

      console.log("[IDENTITY] Routing voice-auth intent:", intent);

      // 🔒 Prevent duplicate REGISTER / LOGIN dispatch
      if (intent === "REGISTER" || intent === "LOGIN") {
        handleIntent(intent);
      }

    };

    window.addEventListener("govind:voice", authHandler);
    return () => window.removeEventListener("govind:voice", authHandler);
  }, []);

  /* ================= VOICE EVENT SUBSCRIPTION (SP2) ================= */
  useEffect(() => {
    const handleVoiceEvent = (e: any) => {
      const event = (e as CustomEvent).detail as VoiceEvent;
      if (!event) return;

      switch (event.type) {
        case "TRANSCRIPT":
          console.log("[RUNTIME → CHAT]", event.text);
          // 🔒 Ground Truth: user speech ALWAYS enters chat log
          addMessage("user", event.text);

          // 🔥 Stage-1: user speech always interrupts TTS
          interruptTTS();

          // 🔐 AUTH FLOWS MUST BYPASS STATE GATING
          if (authModeRef.current === "REGISTER" || authModeRef.current === "LOGIN") {
            handleIntent(event.text);
            return;
          }

          // 🔒 Non-auth commands gated by state machine
          if (canAcceptVoice(stateRef.current)) {
            handleIntent(event.text);
          }
          break;

        case "ERROR":
          console.error("[RUNTIME ERROR]", event.reason);
          addMessage("system", `Voice Error: ${event.reason}`);
          break;
      }
    };

    window.addEventListener("govind:voice_event", handleVoiceEvent);

    //  WAKE Word → UI OPEN (SP2)
    const onWake = () => {
      console.log("[STATE] Wake word detected — opening assistant");
      setIsAssistantOpen(true);
      setState("LISTENING");
      speak("I'm listening.");
    };

    // SLEEP Command (SP2)
    const onSleep = () => {
      console.log("[STATE] Sleep command detected");
      resetSystem();
    };

    window.addEventListener("govind:wake", onWake);
    window.addEventListener("govind:sleep", onSleep);

    return () => {
      window.removeEventListener("govind:voice_event", handleVoiceEvent);
      window.removeEventListener("govind:wake", onWake);
      window.removeEventListener("govind:sleep", onSleep);
    };
  }, []); // Dependencies for closure safety


  useEffect(() => {
    const onWakeStateRestore = () => {
      console.log("[STATE] Wake received — transitioning to AWAKE");
      setState("AWAKE");

      setTimeout(() => {
        setState("LISTENING");
      }, 0);
    };

    window.addEventListener("govind:wake", onWakeStateRestore);

    return () => {
      window.removeEventListener("govind:wake", onWakeStateRestore);
    };
  }, []);


  /* ================= FACE VERIFICATION EVENTS ================= */

  useEffect(() => {
    const onFaceEvent = (e: any) => {
      const { result } = e.detail || {};

      if (result === "FACE_OK") {
        console.log("[FACE] Identity confirmed");
        setAuthStep("VOICE_PIN");
        if (authModeRef.current === "REGISTER") {
          speak("Face captured. Now, please say your four digit voice PIN.");
        } else {
          speak("Identity verified via Face. Please say your voice PIN to log in.");
        }
        return;
      }


      if (result === "FACE_FAIL") {
        console.log("[FACE] Verification failed");
        setAuthStep("FACE");
        setState("WAITING_FOR_FACE");
        speak("Verification failed. Please try again or adjust your lighting.");
        return;
      }


    };

    window.addEventListener("govind:face", onFaceEvent);
    return () => window.removeEventListener("govind:face", onFaceEvent);
  }, []);

  /* ================= SESSION RESTORE (STAGE-2) ================= */

  useEffect(() => {
    const session = restoreSession();

    if (session?.isAuthenticated && session.user) {
      console.log("[SESSION] Restored identity session", session.user);

      setIsAuthenticated(true);
      setUserName(session.user.name || null);
      setState("AUTHENTICATED");
    }
  }, []);


  useEffect(() => {
    const unsub = onAuthChange((user) => {
      if (user) {
        console.log("[AUTH] Firebase user detected:", user.uid);
        // 🔒 Only auto-auth if NOT in the middle of a security flow
        if (!authModeRef.current) {
          setIsAuthenticated(true);
          setUserName(user.email?.split("@")[0] || null);
        }
      } else {
        setIsAuthenticated(false);
        setUserName(null);
      }
    });

    return () => unsub();
  }, []);


  /* ================= 🔓 AUTH MODE UNLOCK (FIX) ================= */
  useEffect(() => {
    if (authStep === "IDLE" && authMode === "REGISTER") {
      setAuthMode(null);

      // ✅ IMPORTANT: return to normal listening mode
      setState("LISTENING");
    }
  }, [authStep, authMode]);

  /* ================= REGISTRATION COMPLETE ================= */

  useEffect(() => {
    if (authMode === "REGISTER" && authStep === "COMPLETE") {
      (async () => {
        try {
          const { email, password, voicePin, faceImage } =
            registrationDataRef.current as RegistrationSession;

          if (!email || !password || !voicePin || !faceImage) {
            throw new Error("Incomplete registration data");
          }

          // 🔐 HASH PIN HERE (SP1 Requirement)
          const voicePinHash = await hashVoicePin(voicePin);

          const regResult = await completeRegistration({
            email,
            password,
            voicePinHash,
            faceImage,
          });

          if (regResult.status === "FAIL") {
            speak(`Registration failed: ${regResult.error}. Please try again or say register to restart.`);
            setAuthStep("EMAIL"); // Back to start or handle better?
            return;
          }

          createSession({
            userId: email,
            email,
            name: email.split("@")[0],
          });

          speak("Registration successful. Welcome to Govind! You are now logged in and verified.");

          setAuthMode(null);
          delete document.body.dataset.authMode;
          setAuthStep("IDLE");
          setIsAuthenticated(true);
          setUserName(email.split("@")[0]);
          navigate("/");
          setIsAssistantOpen(false);
          setState("LISTENING");




        } catch (err) {
          resetSystem();
        }
      })();
    }
  }, [authMode, authStep]);

  /* ================= LOGIN COMPLETE (VOICE PIN STEP) ================= */
  useEffect(() => {
    if (authMode === "LOGIN" && authStep === "COMPLETE") {
      (async () => {
        try {
          const { spokenPin } = loginDataRef.current;
          if (!spokenPin || !userRef.current) throw new Error("Incomplete login data");

          console.log("[AUTH] Final Phase: Verifying Voice PIN");
          const result = await loginStep2Finalize(userRef.current, spokenPin);

          if (result.status === "OK") {
            setIsAuthenticated(true);
            setUserName(result.user.email?.split("@")[0] || null);
            createSession({
              userId: result.user.uid,
              email: result.user.email || undefined,
              name: result.user.email?.split("@")[0],
            });

            setAuthMode(null);
            setAuthStep("IDLE");
            setState("AUTHENTICATED");
            navigate("/");
            setIsAssistantOpen(false);
            setState("LISTENING");
            speak("Access granted. Welcome back.");
          } else if (result.status === "BAD_PIN") {
            speak("Incorrect voice PIN. Please try again.");
            setAuthStep("VOICE_PIN");
          } else {
            speak("Login failed. Please check your credentials.");
            resetSystem();
          }
        } catch (err) {
          console.error("[LOGIN] Final phase failed:", err);
          speak("Critical error during verification.");
        }
      })();
    }
  }, [authMode, authStep]);

  /* ---------------- INTERMEDIATE LOGIN STEPS ---------------- */
  useEffect(() => {
    if (authMode === "LOGIN" && authStep === "FACE") {
      (async () => {
        const { email, password } = loginDataRef.current;
        if (!email || !password) return;

        console.log("[AUTH] Initiating Step 1: Base Auth & Biometric Kickoff");
        const result = await loginStep1BaseAuth(email, password);

        if (result.status === "BIOMETRIC_REQUIRED") {
          userRef.current = result.user;
          (window as any).govind_uid = result.user.uid; // 🔥 Link UID for local face match
          setState("WAITING_FOR_LIVENESS");
          speak("I need to verify your presence. Please look at the camera for 3D depth analysis.");
        } else if (result.status === "NO_FACE") {
          speak("Your face is not registered. Please complete registration first.");
          resetSystem();
        } else {
          speak("Login failed. Please check your credentials.");
          setAuthStep("EMAIL");
        }
      })();
    }
  }, [authMode, authStep]);

  /* ------------------ UTIL ------------------ */

  const addMessage = (role: Message["role"], content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, content, timestamp: new Date() },
    ]);
  };

  /* ------------------ ENABLE ASSISTANT ------------------ */
  const enableAssistant = async () => {
    if (assistantEnabled) return;

    setAssistantEnabled(true);
    setState("LISTENING");

    speak("Govind voice assistant is now enabled.");
  };



  /* ------------------ SPEAKING UTILITY ------------------ */
  const speak = (text: string) => {
    addMessage("assistant", text);
    speakText(text); // TTS service handles mic safety
  };

  /* ------------------ WAKE UP ------------------ */

  const wakeUp = () => {
    isAwakeRef.current = true;
    setState("AWAKE");
    setIsAssistantOpen(true);
  };

  const handleRegistrationStep = (text: string) => {
    handleRegisterSpeech(
      text,
      registrationDataRef.current as RegistrationSession,
      (updater) => {
        if (typeof updater === 'function') {
          registrationDataRef.current = updater(registrationDataRef.current as RegistrationSession);
        } else {
          registrationDataRef.current = updater;
        }
      },
      authStepRef.current as RegisterStep,
      (s: RegisterStep) => setAuthStep(s as AuthStep),
      speak
    );
  };



  const handleLoginStep = (text: string) => {
    handleLoginSpeech(
      text,
      authStepRef.current as LoginStep,
      (s: LoginStep) => {
        if (s === "SUCCESS") {
          setAuthStep("COMPLETE" as AuthStep);
        } else {
          setAuthStep(s as AuthStep);
        }
      },
      speak,
      loginDataRef
    );
  };




  /* ------------------ INTENT HANDLER ------------------ */

  const handleIntent = async (text: string) => {
    console.log("[INTENT] processing:", text, "Auth:", authModeRef.current, "Voice:", voiceModeRef.current, "Step:", composeStepRef.current);

    // � TELEGRAM COMPOSE FLOW (Interceptive & Voice-Guided)
    if (voiceModeRef.current === "TELEGRAM_COMPOSE_FLOW") {
      const lower = text.toLowerCase();

      // Global exit/cancel in the middle of a flow
      if (lower.includes("cancel") || lower.includes("stop") || lower.includes("exit")) {
        speak("Cancelled message.");
        telegram.setIsComposeOpen(false);
        setVoiceMode("GLOBAL");
        setTelegramComposeStep("IDLE");
        return;
      }

      // --- STEP 1: CAPTURE RECIPIENT ---
      if (telegramComposeStepRef.current === "TO") {
        // Clean up the recipient name
        let recipient = text.trim();
        // Store the recipient name
        const newData = { ...telegramComposeDataRef.current, to: recipient };
        telegramComposeDataRef.current = newData;
        // Enhanced matching: case-insensitive with multiple strategies
        const normRecipient = recipient.toLowerCase().trim().replace(/\s+/g, " ");
        let matchingChat = telegram.chats.find(chat => {
          const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
          return normTitle.includes(normRecipient) || normRecipient.includes(normTitle);
        });
        // Fallback: First word match
        if (!matchingChat) {
          const firstWord = normRecipient.split(" ")[0];
          matchingChat = telegram.chats.find(chat => {
            const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
            const chatFirstWord = normTitle.split(" ")[0];
            return chatFirstWord === firstWord;
          });
        }
        if (matchingChat) {
          newData.chatId = matchingChat.id;
          telegramComposeDataRef.current = newData;
          setTelegramComposeStep("CONFIRM_TO");
          speak(`I found ${matchingChat.title}. Is that correct?`);
        } else {
          setTelegramComposeStep("CONFIRM_TO");
          speak(`I'll message ${recipient}. Is that correct? If not, say who you want to message.`);
        }
        return;
      }

      // --- STEP 2: CONFIRM RECIPIENT ---
      if (telegramComposeStepRef.current === "CONFIRM_TO") {
        if (lower.includes("yes") || lower.includes("correct") || lower.includes("yeah") || lower.includes("right")) {
          if (!telegramComposeDataRef.current.chatId) {
            speak("I couldn't find that contact. Please say the name again.");
            setTelegramComposeStep("TO");
            return;
          }
          setTelegramComposeStep("MESSAGE");
          speak("What would you like to say in the message?");
        } else {
          setTelegramComposeStep("TO");
          speak("Who should I send this message to?");
        }
        return;
      }

      // --- STEP 3: CAPTURE MESSAGE ---
      if (telegramComposeStepRef.current === "MESSAGE") {
        const newData = { ...telegramComposeDataRef.current, message: text };
        telegramComposeDataRef.current = newData;
        setTelegramComposeStep("CONFIRM_SEND");
        speak(`Your message is: "${text}". Shall I send it?`);
        return;
      }

      // --- STEP 4: CONFIRM SEND ---
      if (telegramComposeStepRef.current === "CONFIRM_SEND") {
        if (lower.includes("yes") || lower.includes("send") || lower.includes("yeah") || lower.includes("do it")) {
          speak("Sending message now.");
          try {
            const { chatId, message } = telegramComposeDataRef.current;
            if (chatId) {
              await telegram.sendMessage(chatId, message);
              telegram.setIsComposeOpen(false);
              setVoiceMode("GLOBAL");
              setTelegramComposeStep("IDLE");
              speak("Message sent successfully.");
            } else {
              throw new Error("Chat not found");
            }
          } catch (err: any) {
            console.error("Telegram send failed", err);
            speak("I'm sorry, I couldn't send the message. There was an error.");
          }
          return;
        }

        if (lower.includes("no") || lower.includes("stop") || lower.includes("cancel") || lower.includes("change")) {
          speak("Starting over. Who should I message?");
          setTelegramComposeStep("TO");
          const resetData = { to: '', chatId: null, message: '' };
          telegramComposeDataRef.current = resetData;
          return;
        }

        speak("Shall I send the message? Say yes or no.");
        return;
      }
    }

    // �📧 GMAIL COMPOSE FLOW (Interceptive & AI-Powered)
    if (voiceModeRef.current === "COMPOSE_FLOW") {
      const lower = text.toLowerCase();

      // Global exit/cancel in the middle of a flow
      if (lower.includes("cancel") || lower.includes("stop") || lower.includes("exit")) {
        speak("Cancelled composition.");
        gmail.setIsComposeOpen(false);
        setVoiceMode("GLOBAL");
        setComposeStep("IDLE");
        return;
      }

      // --- STEP 1: CAPTURE RECIPIENT ---
      if (composeStepRef.current === "TO") {
        // Clean up formatting (emails shouldn't have spaces)
        let recipient = text.toLowerCase().replace(/\s/g, "");
        // If it got "at gmail dot com" -> "@gmail.com"
        recipient = recipient.replace(/at/g, "@").replace(/dot/g, ".");

        const newData = { ...composeDataRef.current, to: recipient };
        composeDataRef.current = newData;
        gmail.setComposeData(newData);
        setComposeStep("CONFIRM_TO");
        speak(`You want to email ${recipient}. Is that correct?`);
        return;
      }

      // --- STEP 2: CONFIRM RECIPIENT ---
      if (composeStepRef.current === "CONFIRM_TO") {
        if (lower.includes("yes") || lower.includes("correct") || lower.includes("yeah") || lower.includes("right")) {
          setComposeStep("PROMPT");
          speak("Confirmed. What would you like to say in this email?");
        } else {
          setComposeStep("TO");
          speak("Sorry about that. Who should I send this email to?");
        }
        return;
      }

      // --- STEP 3: CAPTURE CONTENT & AI DRAFT ---
      if (composeStepRef.current === "PROMPT") {
        speak("Drafting your email with AI...");
        try {
          const draft = await generateEmailDraft(text, composeDataRef.current.subject);
          const newData = { ...composeDataRef.current, subject: draft.subject, body: draft.body };
          composeDataRef.current = newData;
          gmail.setComposeData(newData);

          setComposeStep("CONFIRM_DRAFT");
          speak("The email is ready. Shall I read it out to you, or just send it?");
        } catch (err: any) {
          console.error("AI Drafting failed", err);
          const errorMsg = err.message?.includes("not found") ? "The AI model is currently unavailable." : "I had trouble drafting that.";
          speak(`${errorMsg} Let's try again. What would you like to say?`);
        }
        return;
      }

      // --- STEP 4: PRE-SEND REVIEW ---
      if (composeStepRef.current === "CONFIRM_DRAFT") {
        const wantsToRead = lower.includes("read") || lower.includes("hear") || (lower.includes("yes") && !lower.includes("send"));
        const wantsToSend = lower.includes("send") || lower.includes("do it") || (lower.includes("yes") && lower.includes("send"));

        if (wantsToRead) {
          const { subject, body } = composeDataRef.current;
          speak(`The subject is "${subject}". The message says: "${body}". Shall I send it now?`);
          setComposeStep("CONFIRM_SEND");
          return;
        }

        if (wantsToSend) {
          speak("Sending email now.");
          try {
            const { to, subject, body } = composeDataRef.current;
            await gmail.sendNewEmail(to, subject, body);
            gmail.setIsComposeOpen(false);
            setVoiceMode("GLOBAL");
            setComposeStep("IDLE");
            speak("Email sent successfully.");
          } catch (err: any) {
            console.error("Manual send failed", err);
            speak("I'm sorry, I couldn't send the email. There was an error with the Gmail service.");
          }
          return;
        }

        if (lower.includes("change") || lower.includes("restart") || lower.includes("no")) {
          speak("Starting over. Who is the recipient?");
          setComposeStep("TO");
          const resetData = { to: "", subject: "", body: "" };
          composeDataRef.current = resetData;
          gmail.setComposeData(resetData);
          return;
        }

        speak("Say 'Read' to hear the draft, or 'Send' to confirm.");
        return;
      }

      // --- STEP 5: FINAL CONFIRMATION ---
      if (composeStepRef.current === "CONFIRM_SEND") {
        if (lower.includes("yes") || lower.includes("send") || lower.includes("yeah") || lower.includes("do it")) {
          speak("Sending email now.");
          try {
            const { to, subject, body } = composeDataRef.current;
            await gmail.sendNewEmail(to, subject, body);
            gmail.setIsComposeOpen(false);
            setVoiceMode("GLOBAL");
            setComposeStep("IDLE");
            speak("Email sent successfully.");
          } catch (err: any) {
            console.error("Final send failed", err);
            speak("I couldn't send the email. It might be a connection issue or a problem with the recipient address.");
          }
          return;
        }

        if (lower.includes("no") || lower.includes("stop") || lower.includes("cancel")) {
          speak("Okay, I won't send it. What should I change? Recipient, or the message?");
          setComposeStep("CONFIRM_DRAFT");
          return;
        }

        speak("Shall I send the email now? Say yes or no.");
        return;
      }
    }

    // 🔴 0. GLOBAL COMMAND PREEMPTION (Safety First)
    if (
      handleGlobalCommand(
        text,
        resetSystem,
        stateRef.current,
        setVoiceMode
      )
    ) {
      return;
    }

    // 🔒 1. HARD AUTH LOCK (Mid-flow session)
    if (authModeRef.current === "REGISTER") {
      handleRegistrationStep(text);
      return;
    }

    if (authModeRef.current === "LOGIN") {
      handleLoginStep(text);
      return;
    }


    // 🧠 3. INTENT DETECTION (SP3)
    const intent = detectIntent(text);

    // 🔐 4. Auth & System Intents
    if (intent.action === "LOGOUT") {
      speak("Logging you out.");
      resetSystem();
      return;
    }

    if (intent.action === "LOGIN") {
      setAuthMode("LOGIN");
      setAuthStep("EMAIL");
      setState("AUTH_LOGIN");
      setRouteIntent("/login");
      speak("Alright. Let’s log you in. Please say your email.");
      return;
    }

    if (intent.action === "REGISTER") {
      setAuthMode("REGISTER");
      setAuthStep("EMAIL");
      setState("AUTH_REGISTER");
      setRouteIntent("/register");
      speak("Alright. Let’s get you registered. Please say your email.");
      return;
    }

    // 🚀 5. Platform Execution (SP4)
    if (intent.platform !== "system") {
      // Specialized handling for OPEN_PLATFORM if UI action is needed
      if (intent.action === "OPEN_PLATFORM" && intent.platform === "gmail") {
        speak("Opening Gmail.");
        setRouteIntent("/gmail");
        return;
      }

      if (intent.action === "OPEN_PLATFORM" && intent.platform === "telegram") {
        speak("Opening Telegram.");
        setRouteIntent("/telegram");
        return;
      }

      // Telegram platform navigation (open telegram)
      if (intent.action === "OPEN_PLATFORM" && intent.platform === "telegram") {
        setRouteIntent("/telegram");
        speak("Opening Telegram.");
        return;
      }

      // Telegram: open chat with person (open chat with... or chat with...)
      if (intent.action === "SEND" && intent.platform === "telegram" && (intent.text.toLowerCase().includes("open chat with") || intent.text.toLowerCase().includes("chat with"))) {
        const recipient = intent.entities.to;
        setRouteIntent("/telegram");
        if (recipient) {
          // Enhanced matching: case-insensitive with multiple strategies
          const normRecipient = recipient.toLowerCase().trim().replace(/\s+/g, " ");
          let matchingChat = telegram.chats.find(chat => {
            const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
            return normTitle.includes(normRecipient) || normRecipient.includes(normTitle);
          });
          // Fallback: First word match
          if (!matchingChat) {
            const firstWord = normRecipient.split(" ")[0];
            matchingChat = telegram.chats.find(chat => {
              const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
              const chatFirstWord = normTitle.split(" ")[0];
              return chatFirstWord === firstWord;
            });
          }
          if (matchingChat) {
            telegram.selectChat(matchingChat); // Always update selectedChat
            speak(`Opening chat with ${matchingChat.title}.`);
            setVoiceMode("GLOBAL");
            telegram.setIsComposeOpen(false);
            return;
          } else {
            speak(`I couldn't find a chat with ${recipient}. Please say the exact name.`);
            return;
          }
        } else {
          speak("Who would you like to chat with?");
          return;
        }
      }

      // Telegram: send message to person (send message to ...)
      if (intent.action === "SEND" && intent.platform === "telegram" && intent.text.toLowerCase().includes("send message to")) {
        const recipient = intent.entities.to;
        setRouteIntent("/telegram");
        if (recipient) {
          // Enhanced matching: case-insensitive with multiple strategies
          const normRecipient = recipient.toLowerCase().trim().replace(/\s+/g, " ");
          
          // Strategy 1: Exact/partial match
          let matchingChat = telegram.chats.find(chat => {
            const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
            return normTitle.includes(normRecipient) || normRecipient.includes(normTitle);
          });
          
          // Strategy 2: First word match (e.g., "Parthiv" matches "Parthiv Sharma")
          if (!matchingChat) {
            const firstWord = normRecipient.split(" ")[0];
            matchingChat = telegram.chats.find(chat => {
              const normTitle = chat.title.toLowerCase().trim().replace(/\s+/g, " ");
              const chatFirstWord = normTitle.split(" ")[0];
              return chatFirstWord === firstWord;
            });
          }
          
          if (matchingChat) {
            telegram.selectChat(matchingChat);
            speak(`Opening chat with ${matchingChat.title}. What message would you like to send?`);
            setVoiceMode("TELEGRAM_COMPOSE_FLOW");
            telegram.setIsComposeOpen(true);
            setTelegramComposeStep("MESSAGE");
            return;
          } else {
            // List available chats for debugging
            const chatNames = telegram.chats.slice(0, 3).map(c => c.title).join(", ");
            speak(`I couldn't find a chat with ${recipient}. Your chats include ${chatNames}. Please say the exact name.`);
            return;
          }
        } else {
          speak("Who would you like to message?");
          setVoiceMode("TELEGRAM_COMPOSE_FLOW");
          telegram.setIsComposeOpen(true);
          setTelegramComposeStep("TO");
          return;
        }
      }

      // Telegram: summarize this chat
      if (intent.action === "SUMMARIZE" && intent.platform === "telegram") {
        if (telegram.selectedChat) {
          // Placeholder: call summarization service here
          speak(`Summarizing chat with ${telegram.selectedChat.title}. (Summary feature coming soon.)`);
        } else {
          speak("Please open a chat first to summarize.");
        }
        return;
      }

      if (intent.action === "VIEW_FOLDER" && intent.platform === "gmail") {
        const folder = intent.entities.query || "inbox";
        speak(`Opening your ${folder} section.`);
        gmail.changeSection(folder);
        // Ensure we are on the gmail page
        setRouteIntent("/gmail");
        return;
      }

      (async () => {
        // 🧠 Inject Context (e.g. Current Email ID for Reply/Summarize)
        if (intent.platform === "gmail" && gmail.selectedEmail?.id) {
          intent.entities.messageId = gmail.selectedEmail.id;
        }

        // Pass complete intent with text
        const result = await routeToPlatform(intent);
        speak(result.message);

        // 🟢 HANDLE UI COMPONENT TRIGGERS
        if (result.data?.type === "OPEN_COMPOSE") {
          gmail.setComposeData({ to: "", subject: "", body: "" }); // Reset
          gmail.setIsComposeOpen(true);
          setVoiceMode("COMPOSE_FLOW");
          setComposeStep("TO");
        }

        if (result.data?.type === "OPEN_COMPOSE_REPLY") {
          const { to, subject, body } = result.data;
          gmail.setComposeData({ to, subject, body });
          gmail.setIsComposeOpen(true);
          // 🔥 INIT REPLY FLOW
          setVoiceMode("COMPOSE_FLOW");
          setComposeStep("PROMPT");
          speak("Alright. What is your reply?");
        }

        // 🟢 SYNC READ EMAIL TO UI
        if (result.success && result.data?.id && intent.action === "READ") {
          // If the adapter already fetched full details, we can just set it
          // But calling openEmail ensures consistency
          gmail.openEmail(result.data.id);
        }
      })();
      return;
    }


    if (intent.action === "UNKNOWN") {
      if (authModeRef.current) return; // Should be handled by auth handlers
      speak("I heard you. You can say register, login, or open Gmail.");
    }

  };




  /* ------------------ PROVIDER ------------------ */

  return (
    <GovindContext.Provider
      value={{
        handleIntent,

        setRegistrationEmail,
        setRegistrationPassword,
        setRegistrationVoicePinHash,
        setRegistrationFaceImage,

        setLoginEmail,
        setLoginPassword,
        setLoginSpokenPin,

        state,
        messages,
        isAssistantOpen,
        setIsAssistantOpen,
        assistantEnabled,
        enableAssistant,

        speak,
        addMessage,
        setState,
        wakeUp,

        authMode,
        authStep,
        setAuthStep,

        isAuthenticated,
        setIsAuthenticated,
        userName,
        setUserName,

        routeIntent,
        setRouteIntent,

        faceImageUrl,
      }}
    >

      {children}
    </GovindContext.Provider>
  );
};
