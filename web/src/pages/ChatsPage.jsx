import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import {
  MessageSquare,
  Send,
  RefreshCw,
  Hash,
  Users,
  Radio,
  User,
  ChevronRight,
  ArrowLeft,
  Eye,
  Share2,
  Trash2,
} from 'lucide-react';

const chatTypeIcon = (type) => {
  switch (type) {
    case 'channel': return <Radio className="w-4 h-4" />;
    case 'supergroup': return <Hash className="w-4 h-4" />;
    case 'group': return <Users className="w-4 h-4" />;
    case 'user': return <User className="w-4 h-4" />;
    default: return <MessageSquare className="w-4 h-4" />;
  }
};

export default function ChatsPage() {
  const { accountId: routeAccountId } = useParams();
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(routeAccountId ? Number(routeAccountId) : null);
  const [chats, setChats] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loadingChats, setLoadingChats] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [sending, setSending] = useState(false);
  const [joinInput, setJoinInput] = useState('');
  const [joiningChannel, setJoiningChannel] = useState(false);
  const messagesEndRef = useRef(null);

  // Load accounts
  useEffect(() => {
    api.listAccounts().then((accs) => {
      const authorized = accs.filter((a) => a.status === 'authorized');
      setAccounts(authorized);
      if (!selectedAccountId && authorized.length > 0) {
        setSelectedAccountId(authorized[0].id);
      }
    });
  }, []);

  // Load chats when account changes
  useEffect(() => {
    if (!selectedAccountId) return;
    setLoadingChats(true);
    setSelectedChat(null);
    setMessages([]);
    api.listChats(selectedAccountId)
      .then(setChats)
      .catch(console.error)
      .finally(() => setLoadingChats(false));
  }, [selectedAccountId]);

  // Load messages when chat changes
  useEffect(() => {
    if (!selectedAccountId || !selectedChat) return;
    setLoadingMessages(true);
    api.listMessages(selectedAccountId, selectedChat.id, 100)
      .then((msgs) => {
        setMessages(msgs.reverse()); // oldest first
        setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      })
      .catch(console.error)
      .finally(() => setLoadingMessages(false));
  }, [selectedAccountId, selectedChat?.id]);

  const handleSync = async () => {
    if (!selectedAccountId || syncing) return;
    setSyncing(true);
    try {
      const result = await api.syncChats(selectedAccountId);
      setChats(result);
    } catch (err) {
      alert(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedAccountId || !selectedChat || sending) return;
    setSending(true);
    try {
      await api.sendMessage(selectedAccountId, selectedChat.id, newMessage.trim());
      setNewMessage('');
      // Refresh messages
      const msgs = await api.listMessages(selectedAccountId, selectedChat.id, 100);
      setMessages(msgs.reverse());
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (err) {
      alert(err.message);
    } finally {
      setSending(false);
    }
  };

  const handleJoinChannel = async () => {
    if (!joinInput.trim() || !selectedAccountId || joiningChannel) return;
    setJoiningChannel(true);
    try {
      const result = await api.joinChannel(selectedAccountId, joinInput.trim());
      setJoinInput('');
      alert('Successfully joined the channel!');
      
      // Reload chat list
      setLoadingChats(true);
      const updatedChats = await api.listChats(selectedAccountId);
      setChats(updatedChats);
      
      // If a chat_id was returned, auto-select it!
      if (result.chat_id) {
        const joinedChat = updatedChats.find(c => c.id === result.chat_id);
        if (joinedChat) {
          setSelectedChat(joinedChat);
        }
      }
    } catch (err) {
      alert(err.message || 'Failed to join channel');
    } finally {
      setJoiningChannel(false);
    }
  };

  const formatDate = (dateStr) => {
    const d = new Date(dateStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
           d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (accounts.length === 0) {
    return (
      <div className="animate-fade-in">
        <h1 className="text-3xl font-bold text-white mb-2">Chats</h1>
        <div className="glass-card p-12 text-center mt-6">
          <MessageSquare className="w-12 h-12 mx-auto mb-3 text-slate-600" />
          <h3 className="text-lg font-medium text-slate-300 mb-1">No connected accounts</h3>
          <p className="text-sm text-slate-500">Connect and authorize a Telegram account first</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Chats</h1>
        </div>
        <div className="flex items-center gap-3">
          {/* Account selector */}
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(Number(e.target.value))}
            className="input-field text-sm w-48"
          >
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.display_name || acc.phone}
              </option>
            ))}
          </select>

          {selectedAccountId && (
            <button
              onClick={async () => {
                if (!confirm('Delete this Telegram account and all its cached data? This action is permanent.')) return;
                try {
                  await api.deleteAccount(selectedAccountId);
                  const accs = await api.listAccounts();
                  const authorized = accs.filter((a) => a.status === 'authorized');
                  setAccounts(authorized);
                  if (authorized.length > 0) {
                    setSelectedAccountId(authorized[0].id);
                  } else {
                    setSelectedAccountId(null);
                    setChats([]);
                    setSelectedChat(null);
                    setMessages([]);
                  }
                } catch (err) {
                  alert(err.message || 'Failed to delete account');
                }
              }}
              className="btn-danger p-2.5 rounded-xl flex items-center justify-center"
              title="Delete Account"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-secondary flex items-center gap-1.5 text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            Sync
          </button>
        </div>
      </div>

      {/* Chat Layout */}
      <div className="glass-card flex h-[calc(100%-4rem)] overflow-hidden">
        {/* Chat List Sidebar */}
        <div className={`w-80 border-r border-slate-800/50 flex flex-col ${selectedChat ? 'hidden md:flex' : 'flex'}`}>
          {/* Join Channel Bar */}
          <div className="p-3 border-b border-slate-800/50 flex gap-2">
            <input
              type="text"
              placeholder="Subscribe by link/username..."
              value={joinInput}
              onChange={(e) => setJoinInput(e.target.value)}
              className="input-field py-1.5 px-3 text-xs flex-1"
            />
            <button
              onClick={handleJoinChannel}
              disabled={joiningChannel || !joinInput.trim()}
              className="btn-primary py-1.5 px-3 text-xs flex items-center justify-center min-w-[50px] font-semibold"
            >
              {joiningChannel ? (
                <div className="w-3.5 h-3.5 border border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                'Join'
              )}
            </button>
          </div>

          {loadingChats ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : chats.length === 0 ? (
            <div className="p-6 text-center text-slate-500">
              <p className="text-sm">No chats. Click Sync to load.</p>
            </div>
          ) : (
            <div className="overflow-y-auto flex-1">
              {chats.map((chat) => (
                <button
                   key={chat.id}
                  onClick={() => setSelectedChat(chat)}
                  className={`w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-white/[0.03] transition-colors border-b border-slate-800/30 ${
                    selectedChat?.id === chat.id ? 'bg-brand-500/10 border-l-2 border-l-brand-500' : ''
                  }`}
                >
                  <div className="w-10 h-10 rounded-xl bg-slate-800/50 border border-slate-700/30 flex items-center justify-center text-slate-400 flex-shrink-0">
                    {chatTypeIcon(chat.chat_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-slate-200 truncate">{chat.title || 'Untitled'}</p>
                      {chat.unread_count > 0 && (
                        <span className="ml-2 px-1.5 py-0.5 rounded-full bg-brand-500 text-white text-[10px] font-bold min-w-[18px] text-center">
                          {chat.unread_count}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between mt-0.5">
                      <p className="text-xs text-slate-500 truncate">
                        {chat.chat_type} <span className="text-[10px] text-slate-600/70 ml-1.5 font-mono">ID: {chat.telegram_chat_id}</span>
                      </p>
                      {chat.last_message_date && (
                        <p className="text-[10px] text-slate-600 ml-2 flex-shrink-0">
                          {formatDate(chat.last_message_date)}
                        </p>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 flex-shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Message View */}
        <div className={`flex-1 flex flex-col ${selectedChat ? 'flex' : 'hidden md:flex'}`}>
          {selectedChat ? (
            <>
              {/* Chat Header */}
              <div className="px-5 py-3 border-b border-slate-800/50 flex items-center gap-3">
                <button
                  onClick={() => setSelectedChat(null)}
                  className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <div className="w-9 h-9 rounded-xl bg-slate-800/50 border border-slate-700/30 flex items-center justify-center text-slate-400">
                  {chatTypeIcon(selectedChat.chat_type)}
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">{selectedChat.title || 'Untitled'}</h3>
                  <p className="text-xs text-slate-500 flex items-center gap-2">
                    <span>{selectedChat.username ? `@${selectedChat.username}` : selectedChat.chat_type}</span>
                    <span className="text-[10px] text-slate-600 font-mono">ID: {selectedChat.telegram_chat_id}</span>
                  </p>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {loadingMessages ? (
                  <div className="flex items-center justify-center h-32">
                    <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : messages.length === 0 ? (
                  <p className="text-center text-slate-500 text-sm mt-8">No messages yet</p>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className="animate-fade-in">
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="text-xs font-medium text-brand-400">
                          {msg.sender_name || 'Unknown'}
                        </span>
                        <span className="text-[10px] text-slate-600">
                          {formatDate(msg.message_date)}
                        </span>
                      </div>
                      <div className="message-bubble message-incoming">
                        <p className="text-sm text-slate-200 whitespace-pre-wrap break-words">
                          {msg.message_text || <span className="text-slate-600 italic">[no text]</span>}
                        </p>
                        
                        {/* Views, Forwards & Reactions */}
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 pt-1.5 border-t border-white/[0.04]">
                          {msg.views !== null && msg.views !== undefined && (
                            <span className="flex items-center text-[10px] text-slate-500">
                              <Eye className="w-3.5 h-3.5 mr-1" />
                              {msg.views}
                            </span>
                          )}
                          {msg.forwards !== null && msg.forwards !== undefined && (
                            <span className="flex items-center text-[10px] text-slate-500">
                              <Share2 className="w-3 h-3 mr-1" />
                              {msg.forwards}
                            </span>
                          )}
                          {msg.reactions?.results?.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {msg.reactions.results.map((r, idx) => {
                                const emoji = r.reaction?.emoticon;
                                if (!emoji) return null;
                                return (
                                  <span key={idx} className="inline-flex items-center px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.05] text-[10px] text-slate-300">
                                    <span className="mr-0.5">{emoji}</span>
                                    <span className="text-slate-400">{r.count}</span>
                                  </span>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Send Message */}
              <form onSubmit={handleSend} className="p-3 border-t border-slate-800/50 flex gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  className="input-field flex-1 text-sm"
                  placeholder="Type a message..."
                />
                <button
                  type="submit"
                  disabled={sending || !newMessage.trim()}
                  className="btn-primary px-4 flex items-center gap-1.5"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-600">
              <div className="text-center">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select a chat to view messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
