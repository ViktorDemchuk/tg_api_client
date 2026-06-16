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
  addQrAccount() {
    return this.request('POST', '/telegram/accounts/qr');
  }
  // Post-auth operations use Telegram user ID
  getAccount(tgUserId) {
    return this.request('GET', `/telegram/accounts/${tgUserId}`);
  }
  deleteAccount(tgUserId) {
    return this.request('DELETE', `/telegram/accounts/${tgUserId}`);
  }
  exportSession(tgUserId) {
    return this.request('GET', `/telegram/accounts/${tgUserId}/session`);
  }
  disconnectAccount(tgUserId) {
    return this.request('POST', `/telegram/accounts/${tgUserId}/disconnect`);
  }

  // Auth-flow operations use local IDs under /pending/
  sendCode(localAccountId) {
    return this.request('POST', `/telegram/pending/${localAccountId}/send-code`);
  }
  submitCode(localAccountId, code, password = null) {
    return this.request('POST', `/telegram/pending/${localAccountId}/submit-code`, { code, password });
  }
  qrRequest(localAccountId) {
    return this.request('POST', `/telegram/pending/${localAccountId}/qr-request`);
  }
  qrWait(localAccountId) {
    return this.request('POST', `/telegram/pending/${localAccountId}/qr-wait`);
  }
  qrSubmitPassword(localAccountId, password) {
    return this.request('POST', `/telegram/pending/${localAccountId}/qr-password`, { password });
  }

  // Chats — all use Telegram IDs
  listChats(tgUserId) {
    return this.request('GET', `/telegram/accounts/${tgUserId}/chats`);
  }
  syncChats(tgUserId) {
    return this.request('POST', `/telegram/accounts/${tgUserId}/chats/sync`);
  }
  listMessages(tgUserId, tgChatId, limit = 50) {
    return this.request('GET', `/telegram/accounts/${tgUserId}/chats/${tgChatId}/messages?limit=${limit}`);
  }
  sendMessage(tgUserId, tgChatId, text) {
    return this.request('POST', `/telegram/accounts/${tgUserId}/chats/${tgChatId}/send`, { text });
  }
  joinChannel(tgUserId, channelUrl) {
    return this.request('POST', `/telegram/accounts/${tgUserId}/channels/join`, { channel_url: channelUrl });
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

  // Admin (keeps local IDs)
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
