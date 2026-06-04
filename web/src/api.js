const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('tg_token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('tg_token', token);
    } else {
      localStorage.removeItem('tg_token');
    }
  }

  async request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const opts = { method, headers };
    if (body && method !== 'GET') {
      opts.body = JSON.stringify(body);
    }

    const resp = await fetch(`${API_BASE}${path}`, opts);

    if (resp.status === 401) {
      this.setToken(null);
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (resp.status === 204) return null;

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || `Request failed: ${resp.status}`);
    }
    return data;
  }

  // Auth
  register(email, username, password) {
    return this.request('POST', '/auth/register', { email, username, password });
  }
  login(email, password) {
    return this.request('POST', '/auth/login', { email, password });
  }
  getProfile() {
    return this.request('GET', '/auth/me');
  }
  updateProfile(username = null, password = null, email = null) {
    const body = {};
    if (username !== null) body.username = username;
    if (password !== null) body.password = password;
    if (email !== null) body.email = email;
    return this.request('PUT', '/auth/me', body);
  }


  // Telegram Accounts
  listAccounts() {
    return this.request('GET', '/telegram/accounts');
  }
  addAccount(phone) {
    return this.request('POST', '/telegram/accounts', { phone });
  }
  deleteAccount(id) {
    return this.request('DELETE', `/telegram/accounts/${id}`);
  }
  exportSession(accountId) {
    return this.request('GET', `/telegram/accounts/${accountId}/session`);
  }

  sendCode(accountId) {
    return this.request('POST', `/telegram/accounts/${accountId}/send-code`);
  }
  submitCode(accountId, code, password = null) {
    return this.request('POST', `/telegram/accounts/${accountId}/submit-code`, { code, password });
  }
  disconnectAccount(accountId) {
    return this.request('POST', `/telegram/accounts/${accountId}/disconnect`);
  }

  // Chats
  listChats(accountId) {
    return this.request('GET', `/telegram/accounts/${accountId}/chats`);
  }
  syncChats(accountId) {
    return this.request('POST', `/telegram/accounts/${accountId}/chats/sync`);
  }
  listMessages(accountId, chatId, limit = 50) {
    return this.request('GET', `/telegram/accounts/${accountId}/chats/${chatId}/messages?limit=${limit}`);
  }
  sendMessage(accountId, chatId, text) {
    return this.request('POST', `/telegram/accounts/${accountId}/chats/${chatId}/send`, { text });
  }
  joinChannel(accountId, channelUrl) {
    return this.request('POST', `/telegram/accounts/${accountId}/channels/join`, { channel_url: channelUrl });
  }

  // API Keys
  listApiKeys() {
    return this.request('GET', '/api-keys');
  }
  createApiKey(name) {
    return this.request('POST', '/api-keys', { name });
  }
  deleteApiKey(id) {
    return this.request('DELETE', `/api-keys/${id}`);
  }

  // Admin
  adminListUsers() {
    return this.request('GET', '/admin/users');
  }
  adminGetUser(id) {
    return this.request('GET', `/admin/users/${id}`);
  }
  adminToggleUser(id, isActive) {
    return this.request('POST', `/admin/users/${id}/disable`, { is_active: isActive });
  }
  adminDeleteUser(id) {
    return this.request('DELETE', `/admin/users/${id}`);
  }
  adminListAccounts() {
    return this.request('GET', '/admin/accounts');
  }
  adminToggleAccount(id, isActive) {
    return this.request('POST', `/admin/accounts/${id}/disable`, { is_active: isActive });
  }
  adminDeleteAccount(id) {
    return this.request('DELETE', `/admin/accounts/${id}`);
  }
  adminAuditLogs(limit = 100) {
    return this.request('GET', `/admin/audit-logs?limit=${limit}`);
  }
  adminStats() {
    return this.request('GET', '/admin/stats');
  }
}

export const api = new ApiClient();
