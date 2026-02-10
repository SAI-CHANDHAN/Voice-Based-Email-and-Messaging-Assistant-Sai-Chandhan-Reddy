// src/pages/Telegram.tsx

import { Layout } from '@/components/layout/Layout';
import { useGovind } from '@/contexts/GovindContext';
import { useTelegram } from '@/contexts/TelegramContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  MessageCircle,
  Send,
  Mic,
  RefreshCcw,
  Link as LinkIcon,
  LogOut,
  Plus,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { TelegramMessage, TelegramChat } from '@/lib/telegram/telegramTypes';

const Telegram = () => {
  const { speak, addMessage } = useGovind();
  const {
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
  } = useTelegram();

  // Connection form state
  const [showConnectDialog, setShowConnectDialog] = useState(false);
  const [connectForm, setConnectForm] = useState({
    apiId: '',
    apiHash: '',
    phoneNumber: '',
  });

  const handleConnect = async () => {
    const apiId = parseInt(connectForm.apiId);
    if (!apiId || !connectForm.apiHash || !connectForm.phoneNumber) {
      speak('Please fill in all connection details');
      return;
    }

    await connect(apiId, connectForm.apiHash, connectForm.phoneNumber);
    setShowConnectDialog(false);
    speak('Connecting to Telegram');
  };

  const handleDisconnect = async () => {
    await disconnect();
    speak('Disconnected from Telegram');
  };

  const handleRefreshChats = async () => {
    await fetchChats();
    speak(`Refreshed. You have ${chats.length} chats.`);
  };

  const handleSelectChat = (chat: TelegramChat) => {
    selectChat(chat);
    addMessage('user', `Open chat with ${chat.title}`);
    speak(`Opening chat with ${chat.title}`);
  };

  const handleSendMessage = async () => {
    if (!composeData.chatId || !composeData.message) {
      speak('Please select a chat and enter a message');
      return;
    }

    await sendMessage(composeData.chatId, composeData.message);
    setIsComposeOpen(false);
    setComposeData({ chatId: null, message: '' });
    speak('Message sent');
  };

  const handleVoiceReadChats = () => {
    addMessage('user', 'Read my Telegram chats');
    
    if (chats.length === 0) {
      speak('You have no chats');
      return;
    }

    const recentChats = chats.slice(0, 5);
    let message = `You have ${chats.length} chats. Recent chats: `;
    recentChats.forEach((chat, idx) => {
      message += `${idx + 1}. ${chat.title}${chat.unreadCount > 0 ? `, ${chat.unreadCount} unread` : ''}. `;
    });
    
    speak(message);
  };

  return (
    <Layout>
      <div className="h-[calc(100vh-4rem)] flex min-w-0"> {/* min-w-0 for flex shrink */}
        {/* Sidebar - Chats List */}
        <div className="w-72 border-r border-border/50 flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-border/50">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Telegram</h2>
              {connected ? (
                <Badge variant="default" className="bg-green-500">
                  Connected
                </Badge>
              ) : (
                <Badge variant="secondary">Not Connected</Badge>
              )}
            </div>

            <div className="flex gap-2">
              {!connected ? (
                <Button
                  className="flex-1"
                  onClick={() => setShowConnectDialog(true)}
                  size="sm"
                >
                  <LinkIcon className="w-4 h-4 mr-2" />
                  Connect
                </Button>
              ) : (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefreshChats}
                    disabled={loading}
                  >
                    <RefreshCcw className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsComposeOpen(true);
                      setComposeData({ ...composeData, chatId: selectedChat?.id || null });
                    }}
                    disabled={!selectedChat}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    New
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDisconnect}
                  >
                    <LogOut className="w-4 h-4" />
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Chats List */}
          {connected && (
            <ScrollArea className="flex-1">
              {loading && chats.length === 0 && (
                <div className="p-4 text-sm text-muted-foreground">
                  Loading chats...
                </div>
              )}
              
              {chats.length === 0 && !loading && (
                <div className="p-4 text-sm text-muted-foreground">
                  No chats found
                </div>
              )}

              <div className="divide-y divide-border/50">
                {chats.map((chat) => (
                  <button
                    key={chat.id}
                    onClick={() => handleSelectChat(chat)}
                    className={cn(
                      'w-full p-3 text-left hover:bg-secondary/50 transition-colors',
                      selectedChat?.id === chat.id && 'bg-secondary'
                    )}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <span className="font-medium text-sm truncate">
                        {chat.title}
                      </span>
                      {chat.unreadCount > 0 && (
                        <Badge variant="default" className="ml-2 text-xs">
                          {chat.unreadCount}
                        </Badge>
                      )}
                    </div>
                    {chat.lastMessage && (
                      <p className="text-xs text-muted-foreground truncate">
                        {chat.lastMessage}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </ScrollArea>
          )}

          {!connected && (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="text-center">
                <MessageCircle className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Connect to Telegram to start messaging
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Main Content - Messages */}
        <div className="flex-1 flex flex-col">
          {selectedChat ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b border-border/50 flex items-center justify-between">
                <div>
                  <h1 className="text-lg font-semibold">{selectedChat.title}</h1>
                  {selectedChat.lastMessage && (
                    <p className="text-xs text-muted-foreground">
                      {messages.length} messages
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={handleVoiceReadChats}>
                    <Mic className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setIsComposeOpen(true);
                      setComposeData({ chatId: selectedChat.id, message: '' });
                    }}
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Send Message
                  </Button>
                </div>
              </div>

              {/* Messages */}
              <ScrollArea className="flex-1 p-4">
                {loading && messages.length === 0 && (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    Loading messages...
                  </div>
                )}

                {messages.length === 0 && !loading && (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    No messages in this chat
                  </div>
                )}

                <div className="space-y-4">
                  {messages.map((message: TelegramMessage) => (
                    <div
                      key={message.id}
                      className={cn(
                        'flex',
                        message.fromSelf ? 'justify-end' : 'justify-start'
                      )}
                    >
                      <Card
                        className={cn(
                          'max-w-[70%]',
                          message.fromSelf
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-secondary'
                        )}
                      >
                        <CardContent className="p-3">
                          {!message.fromSelf && message.senderName && (
                            <p className="text-xs font-semibold mb-1">
                              {message.senderName}
                            </p>
                          )}
                          <p className="text-sm">{message.text}</p>
                          <p className="text-xs opacity-70 mt-1">
                            {message.date instanceof Date 
                              ? message.date.toLocaleString() 
                              : new Date(message.date).toLocaleString()}
                          </p>
                        </CardContent>
                      </Card>
                    </div>
                  ))}
                </div>
              </ScrollArea>

              {error && (
                <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
                  {error}
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageCircle className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                <h2 className="text-xl font-semibold mb-2">
                  {connected ? 'Select a chat' : 'Connect to Telegram'}
                </h2>
                <p className="text-muted-foreground">
                  {connected
                    ? 'Choose a conversation from the sidebar to start messaging'
                    : 'Connect your Telegram account to start messaging hands-free'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Connect Dialog */}
      <Dialog open={showConnectDialog} onOpenChange={setShowConnectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect to Telegram</DialogTitle>
            <DialogDescription>
              Enter your Telegram API credentials to connect. You can get these from{' '}
              <a
                href="https://my.telegram.org"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                my.telegram.org
              </a>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="apiId">API ID</Label>
              <Input
                id="apiId"
                value={connectForm.apiId}
                onChange={(e) =>
                  setConnectForm({ ...connectForm, apiId: e.target.value })
                }
                placeholder="12345678"
              />
            </div>

            <div>
              <Label htmlFor="apiHash">API Hash</Label>
              <Input
                id="apiHash"
                value={connectForm.apiHash}
                onChange={(e) =>
                  setConnectForm({ ...connectForm, apiHash: e.target.value })
                }
                placeholder="abcdef123456..."
              />
            </div>

            <div>
              <Label htmlFor="phoneNumber">Phone Number</Label>
              <Input
                id="phoneNumber"
                value={connectForm.phoneNumber}
                onChange={(e) =>
                  setConnectForm({ ...connectForm, phoneNumber: e.target.value })
                }
                placeholder="+1234567890"
              />
            </div>

            <Button className="w-full" onClick={handleConnect} disabled={loading}>
              {loading ? 'Connecting...' : 'Connect'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Compose Dialog */}
      <Dialog open={isComposeOpen} onOpenChange={setIsComposeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Message</DialogTitle>
            <DialogDescription>
              {selectedChat
                ? `Send a message to ${selectedChat.title}`
                : 'Compose a new message'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="message">Message</Label>
              <Textarea
                id="message"
                value={composeData.message}
                onChange={(e) =>
                  setComposeData({ ...composeData, message: e.target.value })
                }
                placeholder="Type your message..."
                rows={6}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleSendMessage}
              disabled={loading || !composeData.message}
            >
              {loading ? 'Sending...' : 'Send Message'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Telegram;
