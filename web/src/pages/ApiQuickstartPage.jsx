import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Code2, Copy, Check, Terminal, Play, HelpCircle } from 'lucide-react';

export default function ApiQuickstartPage() {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [chats, setChats] = useState([]);
  const [selectedChatId, setSelectedChatId] = useState('');
  const [copied, setCopied] = useState(null);
  const [activeTab, setActiveTab] = useState('curl');
  const [authType, setAuthType] = useState('jwt'); // 'jwt' | 'apikey'
  
  const token = localStorage.getItem('tg_token') || 'YOUR_JWT_TOKEN';
  const apiBase = window.location.origin + '/api';

  useEffect(() => {
    api.listAccounts().then((accs) => {
      const auth = accs.filter(a => a.status === 'authorized');
      setAccounts(auth);
      if (auth.length > 0) {
        setSelectedAccountId(auth[0].id.toString());
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedAccountId) return;
    api.listChats(Number(selectedAccountId)).then((chts) => {
      setChats(chts);
      if (chts.length > 0) {
        setSelectedChatId(chts[0].id.toString());
      } else {
        setSelectedChatId('');
      }
    }).catch(() => {
      setChats([]);
      setSelectedChatId('');
    });
  }, [selectedAccountId]);

  const accId = selectedAccountId || '<account_id>';
  const chtId = selectedChatId || '<chat_db_id>';

  const headerName = authType === 'jwt' ? 'Authorization' : 'X-API-Key';
  const headerValue = authType === 'jwt' ? `Bearer ${token}` : 'YOUR_API_KEY';

  const endpoints = [
    {
      method: 'GET',
      path: '/telegram/accounts',
      desc: 'Retrieve list of all authorized Telegram accounts.',
      payload: null,
      curl: `curl -X GET "${apiBase}/telegram/accounts" \\
     -H "${headerName}: ${headerValue}"`,
      python: `import requests

url = "${apiBase}/telegram/accounts"
headers = {"${headerName}": "${headerValue}"}

response = requests.get(url, headers=headers)
print(response.json())`,
      javascript: `fetch("${apiBase}/telegram/accounts", {
  method: "GET",
  headers: {
    "${headerName}": "${headerValue}"
  }
})
.then(res => res.json())
.then(console.log);`
    },
    {
      method: 'GET',
      path: `/telegram/accounts/${accId}/chats`,
      desc: 'Retrieve list of dialogs/chats for a connected Telegram account.',
      payload: null,
      curl: `curl -X GET "${apiBase}/telegram/accounts/${accId}/chats" \\
     -H "${headerName}: ${headerValue}"`,
      python: `import requests

url = "${apiBase}/telegram/accounts/${accId}/chats"
headers = {"${headerName}": "${headerValue}"}

response = requests.get(url, headers=headers)
print(response.json())`,
      javascript: `fetch("${apiBase}/telegram/accounts/${accId}/chats", {
  method: "GET",
  headers: {
    "${headerName}": "${headerValue}"
  }
})
.then(res => res.json())
.then(console.log);`
    },
    {
      method: 'GET',
      path: `/telegram/accounts/${accId}/chats/${chtId}/messages`,
      desc: 'Retrieve channel/chat messages starting from an optional ISO 8601 datetime timestamp (newer than filter).',
      payload: { limit: 50, since: "2026-06-01T12:00:00Z" },
      curl: `curl -X GET "${apiBase}/telegram/accounts/${accId}/chats/${chtId}/messages?limit=50&since=2026-06-01T12:00:00Z" \\
     -H "${headerName}: ${headerValue}"`,
      python: `import requests

url = "${apiBase}/telegram/accounts/${accId}/chats/${chtId}/messages"
headers = {"${headerName}": "${headerValue}"}
params = {"limit": 50, "since": "2026-06-01T12:00:00Z"}

response = requests.get(url, headers=headers, params=params)
print(response.json())`,
      javascript: `fetch("${apiBase}/telegram/accounts/${accId}/chats/${chtId}/messages?limit=50&since=2026-06-01T12:00:00Z", {
  method: "GET",
  headers: {
    "${headerName}": "${headerValue}"
  }
})
.then(res => res.json())
.then(console.log);`
    },
    {
      method: 'POST',
      path: `/telegram/accounts/${accId}/chats/${chtId}/send`,
      desc: 'Send a new text message to a specific Telegram channel or chat.',
      payload: { text: "Hello channel!" },
      curl: `curl -X POST "${apiBase}/telegram/accounts/${accId}/chats/${chtId}/send" \\
     -H "${headerName}: ${headerValue}" \\
     -H "Content-Type: application/json" \\
     -d '{"text": "Hello channel!"}'`,
      python: `import requests

url = "${apiBase}/telegram/accounts/${accId}/chats/${chtId}/send"
headers = {
    "${headerName}": "${headerValue}",
    "Content-Type": "application/json"
}
data = {"text": "Hello channel!"}

response = requests.post(url, headers=headers, json=data)
print(response.json())`,
      javascript: `fetch("${apiBase}/telegram/accounts/${accId}/chats/${chtId}/send", {
  method: "POST",
  headers: {
    "${headerName}": "${headerValue}",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    text: "Hello channel!"
  })
})
.then(res => res.json())
.then(console.log);`
    },
    {
      method: 'POST',
      path: `/telegram/accounts/${accId}/channels/join`,
      desc: 'Subscribe/join a new Telegram channel or group by username or link.',
      payload: { channel_url: "@durov" },
      curl: `curl -X POST "${apiBase}/telegram/accounts/${accId}/channels/join" \\
     -H "${headerName}: ${headerValue}" \\
     -H "Content-Type: application/json" \\
     -d '{"channel_url": "@durov"}'`,
      python: `import requests

url = "${apiBase}/telegram/accounts/${accId}/channels/join"
headers = {
    "${headerName}": "${headerValue}",
    "Content-Type": "application/json"
}
data = {"channel_url": "@durov"}

response = requests.post(url, headers=headers, json=data)
print(response.json())`,
      javascript: `fetch("${apiBase}/telegram/accounts/${accId}/channels/join", {
  method: "POST",
  headers: {
    "${headerName}": "${headerValue}",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    channel_url: "@durov"
  })
})
.then(res => res.json())
.then(console.log);`
    }
  ];

  const handleCopy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="animate-fade-in space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Code2 className="w-8 h-8 text-brand-500" />
          API Quickstart
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Learn how to integrate our backend REST API into your software, bots, and AI agents.
        </p>
      </div>

      {/* Interactive values builder */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Terminal className="w-5 h-5 text-brand-400" />
          Interactive Request Builder
        </h2>
        <p className="text-xs text-slate-400 mb-6">
          Configure your authentication and parameters below. The code blocks will automatically update with your live credentials and targets!
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
              1. Authentication Method
            </label>
            <select
              value={authType}
              onChange={(e) => setAuthType(e.target.value)}
              className="input-field text-sm w-full"
            >
              <option value="jwt">JWT Token (Bearer)</option>
              <option value="apikey">API Key (X-API-Key)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
              2. Select Telegram Account
            </label>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="input-field text-sm w-full"
            >
              <option value="">-- No Account Selected --</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.display_name || acc.phone} (ID: {acc.id})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
              3. Select Channel / Chat
            </label>
            <select
              value={selectedChatId}
              onChange={(e) => setSelectedChatId(e.target.value)}
              className="input-field text-sm w-full"
              disabled={chats.length === 0}
            >
              <option value="">-- No Chat Selected --</option>
              {chats.map((chat) => (
                <option key={chat.id} value={chat.id}>
                  {chat.title} (Local ID: {chat.id} · TG ID: {chat.telegram_chat_id})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Token Lifetime Notice */}
        {authType === 'jwt' ? (
          <div className="mt-4 p-3.5 rounded-xl bg-brand-500/10 border border-brand-500/20 text-xs text-slate-300 flex items-center gap-2.5">
            <HelpCircle className="w-4 h-4 text-brand-400 flex-shrink-0" />
            <span>
              <strong>JWT Bearer Token:</strong> Expires in <strong>24 hours</strong>. Best suited for secure user-interactive clients and standard frontend sessions. Authenticate with the <code>{`Authorization: Bearer <token>`}</code> header.
            </span>
          </div>
        ) : (
          <div className="mt-4 p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs text-slate-300 flex items-center gap-2.5">
            <HelpCircle className="w-4 h-4 text-cyan-400 flex-shrink-0" />
            <span>
              <strong>API Key:</strong> <strong>Persistent (No Expiration)</strong>. Safe for background daemon tasks, cron-jobs, AI agent integrations, and third-party tools. Exclude bearer headers and pass via the <code>{`X-API-Key: <key>`}</code> header.
            </span>
          </div>
        )}
      </div>

      {/* Language Selector */}
      <div className="flex border-b border-slate-800 gap-6">
        {['curl', 'python', 'javascript'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-sm font-medium transition-colors relative ${
              activeTab === tab ? 'text-brand-400 border-b-2 border-brand-500' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {tab === 'curl' && 'Bash cURL'}
            {tab === 'python' && 'Python (requests)'}
            {tab === 'javascript' && 'JavaScript (fetch)'}
          </button>
        ))}
      </div>

      {/* Endpoints Reference */}
      <div className="space-y-6">
        {endpoints.map((ep, idx) => {
          const codeSnippet = ep[activeTab];
          const isGet = ep.method === 'GET';
          return (
            <div key={idx} className="glass-card p-6 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 rounded text-xs font-extrabold uppercase ${
                    isGet ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                  }`}>
                    {ep.method}
                  </span>
                  <code className="text-sm font-semibold text-white bg-slate-950/60 px-2 py-1 rounded border border-slate-800/40">
                    {ep.path}
                  </code>
                </div>
                <button
                  onClick={() => handleCopy(codeSnippet, idx)}
                  className="btn-secondary py-1.5 px-3 flex items-center gap-1.5 text-xs text-slate-300 self-start md:self-auto"
                >
                  {copied === idx ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400 animate-scale-in" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy Code
                    </>
                  )}
                </button>
              </div>

              <p className="text-sm text-slate-300">{ep.desc}</p>

              {ep.payload && (
                <div className="space-y-1.5">
                  <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">
                    Payload Structure:
                  </span>
                  <pre className="bg-slate-950/80 p-3 rounded-lg border border-slate-900 text-xs text-brand-400 font-mono">
                    {JSON.stringify(ep.payload, null, 2)}
                  </pre>
                </div>
              )}

              <div className="space-y-1.5">
                <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider block">
                  Example Code:
                </span>
                <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800/50 text-xs text-slate-300 font-mono overflow-x-auto whitespace-pre">
                  {codeSnippet}
                </pre>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
