import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import {
  Smartphone,
  MessageSquare,
  Key,
  Activity,
  Plus,
  ArrowRight,
  Copy,
  Check,
  Trash2,
} from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listAccounts(), api.listApiKeys()])
      .then(([acc, keys]) => {
        setAccounts(acc);
        setApiKeys(keys);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const key = await api.createApiKey(newKeyName.trim());
      setCreatedKey(key);
      setNewKeyName('');
      setApiKeys((prev) => [key, ...prev]);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeleteKey = async (id) => {
    if (!confirm('Revoke this API key?')) return;
    try {
      await api.deleteApiKey(id);
      setApiKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(createdKey.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const authorizedCount = accounts.filter((a) => a.status === 'authorized').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Welcome back, {user?.username}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/20">
              <Smartphone className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <div className="stat-value">{accounts.length}</div>
              <div className="stat-label">Telegram Accounts</div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/20">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="stat-value">{authorizedCount}</div>
              <div className="stat-label">Connected</div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/20">
              <MessageSquare className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <button
                onClick={() => navigate('/chats')}
                className="stat-value hover:opacity-80 transition-opacity cursor-pointer"
              >
                Chats →
              </button>
              <div className="stat-label">Open Messenger</div>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/20">
              <Key className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="stat-value">{apiKeys.length}</div>
              <div className="stat-label">API Keys</div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accounts Overview */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Telegram Accounts</h2>
            <button
              onClick={() => navigate('/accounts')}
              className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1 transition-colors"
            >
              Manage <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {accounts.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <Smartphone className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p>No Telegram accounts connected</p>
              <button
                onClick={() => navigate('/accounts')}
                className="btn-primary mt-3 text-sm"
              >
                <Plus className="w-4 h-4 inline mr-1" /> Add Account
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {accounts.slice(0, 5).map((acc) => (
                <div
                  key={acc.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-800/30 border border-slate-700/30"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-brand-500/20 flex items-center justify-center text-xs font-medium text-brand-400">
                      {acc.display_name?.[0] || acc.phone?.[0] || '?'}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        {acc.display_name || acc.phone}
                      </p>
                      <p className="text-xs text-slate-500">{acc.phone}</p>
                    </div>
                  </div>
                  <span className={`status-badge status-${acc.status}`}>
                    {acc.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* API Keys */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4">API Keys</h2>

          {/* Created key notification */}
          {createdKey && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <p className="text-sm text-emerald-400 font-medium mb-1">New API key created!</p>
              <div className="flex items-center gap-2">
                <code className="text-xs text-slate-300 bg-slate-800/50 px-2 py-1 rounded flex-1 truncate">
                  {createdKey.api_key}
                </code>
                <button
                  onClick={handleCopyKey}
                  className="p-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-slate-400" />
                  )}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Save this key — it won't be shown again.</p>
            </div>
          )}

          {/* Create form */}
          <form onSubmit={handleCreateKey} className="flex gap-2 mb-4">
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              className="input-field flex-1 text-sm"
              placeholder="Key name (e.g., 'MCP Agent')"
            />
            <button type="submit" className="btn-primary text-sm whitespace-nowrap">
              <Plus className="w-4 h-4 inline mr-1" /> Create
            </button>
          </form>

          {/* Keys list */}
          {apiKeys.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">No API keys yet</p>
          ) : (
            <div className="space-y-2">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-800/30 border border-slate-700/30"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-200">{key.name}</p>
                    <p className="text-xs text-slate-500">
                      {key.key_prefix}•••• · Created {new Date(key.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteKey(key.id)}
                    className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Revoke"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
