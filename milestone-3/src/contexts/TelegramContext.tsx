// src/contexts/TelegramContext.tsx

import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { TelegramMessage, TelegramChat } from "@/lib/telegram/telegramTypes";

// Backend API base URL
const API_BASE = "http://localhost:5001/api/telegram";

interface TelegramContextType {
  // Connection state
  connected: boolean;
  loading: boolean;
  error: string | null;

  // Data
  chats: TelegramChat[];
  messages: TelegramMessage[];
  selectedChat: TelegramChat | null;

  // Actions
  connect: (apiId: number, apiHash: string, phoneNumber: string) => Promise<void>;
  disconnect: () => Promise<void>;
  fetchChats: () => Promise<void>;
  fetchMessages: (chatId: number, limit?: number) => Promise<void>;
  sendMessage: (chatId: number, text: string) => Promise<void>;
  selectChat: (chat: TelegramChat | null) => void;
  
  // Compose state
  isComposeOpen: boolean;
  setIsComposeOpen: (open: boolean) => void;
  composeData: { chatId: number | null; message: string };
  setComposeData: (data: { chatId: number | null; message: string }) => void;

  clearError: () => void;
}

const TelegramContext = createContext<TelegramContextType | undefined>(undefined);

export const TelegramProvider = ({ children }: { children: ReactNode }) => {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [chats, setChats] = useState<TelegramChat[]>([]);
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [selectedChat, setSelectedChat] = useState<TelegramChat | null>(null);
  
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [composeData, setComposeData] = useState<{ chatId: number | null; message: string }>({
    chatId: null,
    message: "",
  });

  const fetchChats = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log('[TELEGRAM] Fetching chats from API...');
      const response = await fetch(`${API_BASE}/chats?limit=20`, {
        credentials: 'include',
      });

      const data = await response.json();
      console.log('[TELEGRAM] Chats API response:', data);

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch chats');
      }
      
      console.log('[TELEGRAM] Setting chats:', data.chats);
      setChats(data.chats || []);
    } catch (err: any) {
      console.error('[TELEGRAM] Fetch chats error:', err);
      setError(err.message || "Failed to fetch chats");
    } finally {
      setLoading(false);
    }
  };

  // Check if already connected on mount
  useEffect(() => {
    const checkConnection = async () => {
      try {
        console.log('[TELEGRAM] Checking connection status...');
        const response = await fetch(`${API_BASE}/status`, {
          credentials: 'include',
        });
        const data = await response.json();
        console.log('[TELEGRAM] Status response:', data);
        
        const isConnected = data.connected && data.authorized;
        setConnected(isConnected);
        
        // Store connection state in localStorage
        if (isConnected) {
          localStorage.setItem('telegram_connected', 'true');
          console.log('[TELEGRAM] Connection restored, fetching chats...');
          await fetchChats();
        } else {
          localStorage.removeItem('telegram_connected');
        }
      } catch (err) {
        console.log("[TELEGRAM] Backend not available or not connected", err);
        localStorage.removeItem('telegram_connected');
      }
    };

    checkConnection();
  }, []);

  const connect = async (apiId: number, apiHash: string, phoneNumber: string) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          apiId,
          apiHash,
          phoneNumber,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Connection failed');
      }

      if (data.needsCode) {
        // Prompt user for verification code
        const code = prompt('Enter the verification code sent to your Telegram:');
        if (code) {
          console.log('[TELEGRAM] Sending verification code...');
          const verifyResponse = await fetch(`${API_BASE}/verify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ code }),
          });

          const verifyData = await verifyResponse.json();
          console.log('[TELEGRAM] Verify response:', verifyData);
          
          if (!verifyData.success) {
            throw new Error(verifyData.error || 'Verification failed');
          }
          
          console.log('[TELEGRAM] Verification successful!');
        } else {
          throw new Error('Verification code required');
        }
      }

      setConnected(true);
      localStorage.setItem('telegram_connected', 'true');
      console.log('[TELEGRAM] Connected! Fetching chats...');
      
      // Auto-fetch chats after connection
      await fetchChats();
      console.log('[TELEGRAM] Chats fetched successfully!');
    } catch (err: any) {
      setError(err.message || "Failed to connect to Telegram");
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const disconnect = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_BASE}/disconnect`, {
        method: 'POST',
        credentials: 'include',
      });

      const data = await response.json();
      
      setConnected(false);
      localStorage.removeItem('telegram_connected');
      setChats([]);
      setMessages([]);
      setSelectedChat(null);
    } catch (err: any) {
      setError(err.message || "Failed to disconnect");
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (chatId: number, limit: number = 50) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/messages/${chatId}?limit=${limit}`, {
        credentials: 'include',
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch messages');
      }
      
      // Convert date strings back to Date objects
      const messagesWithDates = data.messages.map((msg: any) => ({
        ...msg,
        date: new Date(msg.date),
      }));
      
      setMessages(messagesWithDates);
    } catch (err: any) {
      setError(err.message || "Failed to fetch messages");
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (chatId: number, text: string) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ chatId, text }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to send message');
      }
      
      // Refresh messages after sending
      await fetchMessages(chatId);
    } catch (err: any) {
      setError(err.message || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const selectChat = (chat: TelegramChat | null) => {
    setSelectedChat(chat);
    if (chat) {
      fetchMessages(chat.id);
    } else {
      setMessages([]);
    }
  };

  const clearError = () => setError(null);

  return (
    <TelegramContext.Provider
      value={{
        connected,
        loading,
        error,
        chats,
        messages,
        selectedChat,
        connect,
        disconnect,
        fetchChats,
        fetchMessages,
        sendMessage,
        selectChat,
        isComposeOpen,
        setIsComposeOpen,
        composeData,
        setComposeData,
        clearError,
      }}
    >
      {children}
    </TelegramContext.Provider>
  );
};

export const useTelegram = () => {
  const context = useContext(TelegramContext);
  if (!context) {
    throw new Error("useTelegram must be used within TelegramProvider");
  }
  return context;
};
