import React, { useState } from 'react';
import { Layers, Copy, Check, Terminal, Server, Cpu, Info } from 'lucide-react';

export default function McpQuickstartPage() {
  const [copied, setCopied] = useState(null);
  const mcpBase = window.location.origin + '/mcp/sse';
  const apiKey = 'YOUR_API_KEY';

  const claudeConfig = `{
  "mcpServers": {
    "tg-api-client": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/client-cli",
        "sse",
        "${mcpBase}?api_key=${apiKey}"
      ]
    }
  }
}`;

  const mcpTools = [
    {
      name: 'list_telegram_accounts',
      desc: 'Retrieve list of all authorized Telegram accounts owned by the user.',
      params: {}
    },
    {
      name: 'list_chats',
      desc: 'List dialogs/chats (groups, channels, users) for a specific Telegram account.',
      params: {
        account_id: { type: 'integer', desc: 'Telegram account ID' }
      }
    },
    {
      name: 'get_recent_messages',
      desc: 'Get cached recent messages from a channel or chat.',
      params: {
        account_id: { type: 'integer', desc: 'Telegram account ID' },
        chat_id: { type: 'integer', desc: 'Chat local ID' },
        limit: { type: 'integer', desc: 'Optional: Number of messages to return (default: 20)' }
      }
    },
    {
      name: 'send_telegram_message',
      desc: 'Send a new text message to a specific Telegram channel or chat.',
      params: {
        account_id: { type: 'integer', desc: 'Telegram account ID' },
        chat_id: { type: 'integer', desc: 'Chat local ID' },
        text: { type: 'string', desc: 'Message text to send' }
      }
    },
    {
      name: 'search_messages',
      desc: 'Search all cached messages across accounts by keyword.',
      params: {
        query: { type: 'string', desc: 'Keyword query text' },
        account_id: { type: 'integer', desc: 'Optional: limit to specific account' },
        limit: { type: 'integer', desc: 'Optional: Maximum results (default: 50)' }
      }
    },
    {
      name: 'subscribe_to_channel',
      desc: 'Subscribe/join a new Telegram channel or group by username or link.',
      params: {
        account_id: { type: 'integer', desc: 'Telegram account ID' },
        channel_url: { type: 'string', desc: 'Channel username (e.g. "@durov") or link' }
      }
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
          <Layers className="w-8 h-8 text-brand-500" />
          MCP Quickstart
        </h1>
        <p className="text-sm text-slate-400 mt-2">
          Connect our Telegram client as a Model Context Protocol (MCP) server to Claude Desktop, Cursor, or your custom LLM agents.
        </p>
      </div>

      {/* Connection Info */}
      <div className="glass-card p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Server className="w-5 h-5 text-brand-400" />
          SSE Connection URL
        </h2>
        <p className="text-sm text-slate-300">
          Our MCP server exposes a standard Server-Sent Events (SSE) gateway. Connect your MCP client to the following endpoint:
        </p>
        <div className="flex items-center justify-between gap-3 bg-slate-950 p-3 rounded-lg border border-slate-900">
          <code className="text-xs text-brand-400 font-mono select-all break-all">
            {mcpBase}?api_key=YOUR_API_KEY
          </code>
          <button
            onClick={() => handleCopy(`${mcpBase}?api_key=YOUR_API_KEY`, 'url')}
            className="text-slate-500 hover:text-white transition-colors"
          >
            {copied === 'url' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
        <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-lg flex gap-3 text-xs text-slate-300">
          <Info className="w-5 h-5 text-brand-400 flex-shrink-0" />
          <div>
            <strong>Authentication Note:</strong> Make sure to replace <code className="bg-white/5 px-1 py-0.5 rounded text-brand-400">YOUR_API_KEY</code> with a valid API key generated from the <strong>Dashboard</strong> page.
          </div>
        </div>
      </div>

      {/* Claude Desktop Config */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-brand-400" />
            Claude Desktop Configuration
          </h2>
          <button
            onClick={() => handleCopy(claudeConfig, 'config')}
            className="btn-secondary py-1.5 px-3 flex items-center gap-1.5 text-xs text-slate-300"
          >
            {copied === 'config' ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400 animate-scale-in" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                Copy Config
              </>
            )}
          </button>
        </div>
        <p className="text-sm text-slate-300">
          To give Claude Desktop access to your Telegram client, open your configuration file at:
          <br />
          <code className="text-xs bg-slate-950 px-1.5 py-0.5 rounded text-slate-400 font-mono mt-1 inline-block">
            %APPDATA%\\Claude\\claude_desktop_config.json
          </code>
          <br />
          And merge the following JSON configuration into your <code className="text-slate-400">mcpServers</code> section:
        </p>
        <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800/50 text-xs text-slate-300 font-mono overflow-x-auto whitespace-pre">
          {claudeConfig}
        </pre>
      </div>

      {/* Available Tools Catalog */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Terminal className="w-5 h-5 text-brand-400" />
          Exposed MCP Tools Catalog ({mcpTools.length} tools)
        </h2>
        <p className="text-xs text-slate-400">
          When connected, your AI agents will have native access to the following programmatic capabilities:
        </p>

        <div className="space-y-4">
          {mcpTools.map((tool, idx) => (
            <div key={idx} className="glass-card p-5 space-y-3">
              <div className="flex items-center gap-2">
                <code className="text-sm font-semibold text-brand-400 bg-brand-500/5 px-2.5 py-0.5 rounded-lg border border-brand-500/10 font-mono">
                  {tool.name}
                </code>
              </div>
              <p className="text-xs text-slate-300">{tool.desc}</p>
              
              {Object.keys(tool.params).length > 0 ? (
                <div className="space-y-1.5">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider block">
                    Parameters Schema:
                  </span>
                  <div className="bg-slate-950/50 rounded-lg border border-slate-900/50 p-3 space-y-2">
                    {Object.entries(tool.params).map(([pName, pMeta]) => (
                      <div key={pName} className="flex flex-col md:flex-row md:items-baseline gap-1.5 text-[11px]">
                        <code className="text-white font-mono font-semibold">{pName}</code>
                        <span className="text-slate-600 font-mono">({pMeta.type})</span>
                        <span className="text-slate-400">— {pMeta.desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <span className="text-[10px] text-slate-600 font-semibold uppercase tracking-wider block">
                  Parameters Schema: No input parameters required.
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
