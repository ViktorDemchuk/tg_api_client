import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { QRCodeSVG } from 'qrcode.react';
import {
  Plus,
  Phone,
  Trash2,
  Send,
  KeyRound,
  Lock,
  Unplug,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  X,
  Download,
  Copy,
  Check,
  QrCode,
} from 'lucide-react';

export default function AccountsPage() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [authModal, setAuthModal] = useState(null); // { accountId, step: 'code_sent' | 'password_required' }
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');

  const [exportSessionData, setExportSessionData] = useState(null); // { phone, session_string }
  const [copied, setCopied] = useState(false);
  const [addMethod, setAddMethod] = useState('phone'); // 'phone' | 'qr'
  const [qrModal, setQrModal] = useState(null); // { accountId, qrUrl, step, error }
  const [countdown, setCountdown] = useState(30);

  const handleExportSession = async (accountId) => {
    setActionLoading(true);
    try {
      const data = await api.exportSession(accountId);
      setExportSessionData(data);
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const fetchAccounts = () => {
    api.listAccounts()
      .then(setAccounts)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchAccounts(); }, []);

  // Polling for QR Scan success
  useEffect(() => {
    if (!qrModal || qrModal.step !== 'scanning') return;

    let active = true;
    let timeoutId;

    const poll = async () => {
      try {
        const res = await api.qrWait(qrModal.accountId);
        if (!active) return;

        if (res.authorized) {
          setQrModal(null);
          fetchAccounts();
        } else if (res.needs_password) {
          setQrModal(prev => ({ ...prev, step: 'password_required', error: null }));
        } else {
          timeoutId = setTimeout(poll, 4000);
        }
      } catch (err) {
        if (!active) return;
        setQrModal(prev => ({ ...prev, step: 'error', error: err.message }));
      }
    };

    timeoutId = setTimeout(poll, 2000);

    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [qrModal?.step, qrModal?.accountId]);

  // QR Countdown Timer
  useEffect(() => {
    if (!qrModal || qrModal.step !== 'scanning') return;

    setCountdown(30);

    const intervalId = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(intervalId);
          setQrModal((modal) => {
            if (modal && modal.step === 'scanning') {
              return { ...modal, step: 'expired' };
            }
            return modal;
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(intervalId);
  }, [qrModal?.step, qrModal?.accountId, qrModal?.qrUrl]);

  const handleAddAccount = async (e) => {
    e.preventDefault();
    setError('');
    setActionLoading(true);
    try {
      if (addMethod === 'phone') {
        await api.addAccount(phone);
        setPhone('');
      } else {
        await api.addQrAccount();
      }
      setShowAddModal(false);
      fetchAccounts();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartQrAuth = async (accountId) => {
    setQrModal({ accountId, qrUrl: null, step: 'requesting', error: null });
    try {
      const res = await api.qrRequest(accountId);
      if (res.authorized) {
        setQrModal(null);
        fetchAccounts();
      } else if (res.qr_link) {
        setQrModal({ accountId, qrUrl: res.qr_link, step: 'scanning', error: null });
      } else {
        throw new Error('Failed to get QR code login link');
      }
    } catch (err) {
      setQrModal({ accountId, qrUrl: null, step: 'error', error: err.message });
    }
  };

  const handleSubmitQrPassword = async (e) => {
    e.preventDefault();
    if (!qrModal) return;
    setQrModal(prev => ({ ...prev, error: null }));
    setActionLoading(true);
    try {
      const res = await api.qrSubmitPassword(qrModal.accountId, password);
      if (res.authorized) {
        setQrModal(null);
        setPassword('');
        fetchAccounts();
      } else {
        setQrModal(prev => ({ ...prev, error: 'Authorization failed. Please check your password.' }));
      }
    } catch (err) {
      setQrModal(prev => ({ ...prev, error: err.message }));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSendCode = async (accountId) => {
    setError('');
    setActionLoading(true);
    try {
      const result = await api.sendCode(accountId);
      if (result.authorized) {
        fetchAccounts();
      } else {
        setAuthModal({ accountId, step: 'code_sent' });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitCode = async (e) => {
    e.preventDefault();
    if (!authModal) return;
    setError('');
    setActionLoading(true);
    try {
      const result = await api.submitCode(authModal.accountId, code, password || null);
      if (result.needs_password) {
        setAuthModal({ ...authModal, step: 'password_required' });
      } else if (result.authorized) {
        setAuthModal(null);
        setCode('');
        setPassword('');
        fetchAccounts();
      } else {
        setError('Authorization failed. Please try again.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async (accountId) => {
    if (!confirm('Disconnect this Telegram account?')) return;
    try {
      await api.disconnectAccount(accountId);
      fetchAccounts();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (accountId) => {
    if (!confirm('Delete this Telegram account and all its data?')) return;
    try {
      await api.deleteAccount(accountId);
      fetchAccounts();
    } catch (err) {
      alert(err.message);
    }
  };

  const statusIcon = (status) => {
    switch (status) {
      case 'authorized': return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'code_sent': return <Clock className="w-4 h-4 text-blue-400" />;
      case 'pending': return <Clock className="w-4 h-4 text-amber-400" />;
      default: return <AlertCircle className="w-4 h-4 text-red-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Telegram Accounts</h1>
          <p className="text-slate-400 mt-1">Connect and manage your Telegram accounts</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Account
        </button>
      </div>

      {/* Accounts Grid */}
      {accounts.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Phone className="w-12 h-12 mx-auto mb-3 text-slate-600" />
          <h3 className="text-lg font-medium text-slate-300 mb-1">No accounts yet</h3>
          <p className="text-sm text-slate-500 mb-4">Connect your first Telegram account to get started</p>
          <button onClick={() => setShowAddModal(true)} className="btn-primary">
            <Plus className="w-4 h-4 inline mr-1" /> Add Account
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {accounts.map((acc) => {
            const isQrPending = acc.phone.startsWith('+QR_PENDING_');
            return (
              <div key={acc.id} className="glass-card p-5 animate-fade-in">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand-500/20 to-cyan-500/20 border border-brand-500/30 flex items-center justify-center">
                      {isQrPending ? (
                        <QrCode className="w-6 h-6 text-brand-400" />
                      ) : (
                        <Phone className="w-6 h-6 text-brand-400" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">
                        {isQrPending ? (acc.display_name || 'QR Code Account') : (acc.display_name || acc.phone)}
                      </h3>
                      <p className="text-sm text-slate-500">
                        {isQrPending ? 'QR Code Login' : acc.phone}
                      </p>
                    </div>
                  </div>
                  <span className={`status-badge status-${acc.status}`}>
                    {statusIcon(acc.status)}
                    {acc.status}
                  </span>
                </div>

                {acc.last_error && (
                  <div className="mb-3 p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                    {acc.last_error}
                  </div>
                )}

                {!acc.is_active && (
                  <div className="mb-3 p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 flex items-center gap-2">
                    <Lock className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>Greylist: Waiting for admin approval</span>
                  </div>
                )}

                <div className="text-xs text-slate-500 mb-4">
                  {acc.telegram_user_id && <p>Telegram ID: {acc.telegram_user_id}</p>}
                  <p>Added: {new Date(acc.created_at).toLocaleString()}</p>
                </div>

                <div className="flex gap-2 flex-wrap">
                  {acc.status === 'pending' && (
                    isQrPending ? (
                      <button
                        onClick={() => handleStartQrAuth(acc.id)}
                        disabled={!acc.is_active}
                        className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <QrCode className="w-3.5 h-3.5" /> Authenticate via QR
                      </button>
                    ) : (
                      <button
                        onClick={() => handleSendCode(acc.id)}
                        disabled={!acc.is_active}
                        className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Send className="w-3.5 h-3.5" /> Send Code
                      </button>
                    )
                  )}
                  {acc.status === 'code_sent' && (
                    <button
                      onClick={() => setAuthModal({ accountId: acc.id, step: 'code_sent' })}
                      disabled={!acc.is_active}
                      className="btn-primary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <KeyRound className="w-3.5 h-3.5" /> Enter Code
                    </button>
                  )}
                  {acc.status === 'error' && (
                    isQrPending ? (
                      <button
                        onClick={() => handleStartQrAuth(acc.id)}
                        disabled={!acc.is_active}
                        className="btn-secondary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Retry QR
                      </button>
                    ) : (
                      <button
                        onClick={() => handleSendCode(acc.id)}
                        disabled={!acc.is_active}
                        className="btn-secondary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Retry
                      </button>
                    )
                  )}
                  {acc.status === 'authorized' && (
                    <>
                      <button
                        onClick={() => handleExportSession(acc.id)}
                        className="btn-secondary text-xs flex items-center gap-1.5"
                      >
                        <Download className="w-3.5 h-3.5" /> Export Session
                      </button>
                      <button
                        onClick={() => handleDisconnect(acc.id)}
                        disabled={!acc.is_active}
                        className="btn-secondary text-xs flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Unplug className="w-3.5 h-3.5" /> Disconnect
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(acc.id)}
                    className="btn-danger text-xs flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Account Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => { setShowAddModal(false); setAddMethod('phone'); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Add Telegram Account</h2>
              <button onClick={() => { setShowAddModal(false); setAddMethod('phone'); }} className="p-1 text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Method Tabs */}
            <div className="flex gap-2 bg-slate-800/55 rounded-xl p-1 mb-4">
              <button
                type="button"
                onClick={() => setAddMethod('phone')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${
                  addMethod === 'phone'
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Phone className="w-4 h-4" />
                Phone Number
              </button>
              <button
                type="button"
                onClick={() => setAddMethod('qr')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${
                  addMethod === 'qr'
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <QrCode className="w-4 h-4" />
                QR Code
              </button>
            </div>

            {error && (
              <div className="mb-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}
            <form onSubmit={handleAddAccount} className="space-y-4">
              {addMethod === 'phone' ? (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">Phone Number</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="input-field input-with-icon"
                      placeholder="+1234567890"
                      required={addMethod === 'phone'}
                    />
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/50 space-y-2">
                  <p className="text-sm text-slate-300 font-semibold flex items-center gap-1.5">
                    <QrCode className="w-4 h-4 text-brand-400" /> Connect via QR code
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    This adds a temporary account session. Just like standard phone connections, it starts in a pending greylisted state and must be approved by the administrator before you can scan the QR code.
                  </p>
                </div>
              )}
              <button type="submit" disabled={actionLoading} className="btn-primary w-full">
                {actionLoading ? 'Adding...' : 'Add Account'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Auth Code Modal */}
      {authModal && (
        <div className="modal-overlay" onClick={() => setAuthModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">
                {authModal.step === 'password_required' ? 'Two-Factor Authentication' : 'Enter Code'}
              </h2>
              <button onClick={() => setAuthModal(null)} className="p-1 text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            {error && (
              <div className="mb-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}
            <form onSubmit={handleSubmitCode} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">
                  Telegram Code
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    className="input-field input-with-icon"
                    placeholder="12345"
                    required
                  />
                </div>
              </div>
              {authModal.step === 'password_required' && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    2FA Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input-field input-with-icon"
                      placeholder="Your 2FA password"
                      required
                    />
                  </div>
                </div>
              )}
              <button type="submit" disabled={actionLoading} className="btn-primary w-full">
                {actionLoading ? 'Verifying...' : 'Verify'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* QR Authentication Modal */}
      {qrModal && (
        <div className="modal-overlay" onClick={() => setQrModal(null)}>
          <div className="modal-content max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <QrCode className="w-5 h-5 text-brand-400" />
                Telegram QR Authentication
              </h2>
              <button onClick={() => setQrModal(null)} className="p-1 text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {qrModal.error && (
              <div className="mb-3 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {qrModal.error}
              </div>
            )}

            <div className="flex flex-col items-center justify-center py-6 space-y-4">
              {qrModal.step === 'requesting' && (
                <div className="flex flex-col items-center space-y-2">
                  <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-slate-400">Requesting login code from Telegram...</p>
                </div>
              )}

              {qrModal.step === 'scanning' && qrModal.qrUrl && (
                <>
                  <div className="p-4 bg-white rounded-2xl shadow-xl flex items-center justify-center">
                    <QRCodeSVG value={qrModal.qrUrl} size={220} />
                  </div>
                  <div className="text-center space-y-2 max-w-xs">
                    <p className="text-sm text-white font-medium">Scan this code with your mobile app</p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Open Telegram settings &gt; Devices &gt; Link Desktop Device, then point your camera here.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-brand-400 bg-brand-500/10 px-3 py-1 rounded-full mt-2">
                    <Clock className="w-3.5 h-3.5 animate-pulse" />
                    <span>Expires in <strong className="font-bold font-mono text-white text-sm">{countdown}</strong> seconds</span>
                  </div>
                </>
              )}

              {qrModal.step === 'expired' && (
                <div className="text-center space-y-4 py-4 w-full">
                  <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-full flex items-center justify-center mx-auto text-red-500">
                    <Clock className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-base font-semibold text-white">QR Code Expired</h3>
                    <p className="text-xs text-slate-400 max-w-xs mx-auto">
                      For security, Telegram login QR codes are only valid for 30 seconds. Please request a new one.
                    </p>
                  </div>
                  <button
                    onClick={() => handleStartQrAuth(qrModal.accountId)}
                    className="btn-primary text-xs flex items-center gap-1.5 mx-auto"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh QR Code
                  </button>
                </div>
              )}

              {qrModal.step === 'password_required' && (
                <form onSubmit={handleSubmitQrPassword} className="w-full space-y-4">
                  <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">Two-Factor Authentication (2FA) Required</p>
                      <p className="mt-0.5">Please enter the 2FA password set for your Telegram account.</p>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                      2FA Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-slate-500" />
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="input-field input-with-icon"
                        placeholder="Your Telegram 2FA password"
                        required
                      />
                    </div>
                  </div>
                  <button type="submit" disabled={actionLoading} className="btn-primary w-full">
                    {actionLoading ? 'Verifying...' : 'Verify Password'}
                  </button>
                </form>
              )}

              {qrModal.step === 'error' && (
                <div className="text-center space-y-4">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
                  <p className="text-sm text-slate-300">{qrModal.error || 'Could not initialize QR authentication.'}</p>
                  <button onClick={() => handleStartQrAuth(qrModal.accountId)} className="btn-primary text-xs">
                    <RefreshCw className="w-3.5 h-3.5 inline mr-1.5" /> Retry Request
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Export Session Modal */}
      {exportSessionData && (
        <div className="modal-overlay" onClick={() => setExportSessionData(null)}>
          <div className="modal-content max-w-lg" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-brand-400" />
                Export Telegram Session
              </h2>
              <button onClick={() => setExportSessionData(null)} className="p-1 text-slate-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Warning Box */}
            <div className="mb-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-start gap-3 animate-fade-in">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-400" />
              <div className="space-y-1">
                <p className="font-bold uppercase tracking-wider">Crucial Security Warning</p>
                <p className="leading-relaxed">
                  This session key is extremely sensitive credentials. Anyone with access to this key can take full, unhindered control of your Telegram account. Never share it with anyone!
                </p>
              </div>
            </div>

            {/* Session key display */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Session Key ({exportSessionData.phone})
                </label>
                {exportSessionData.session_string ? (
                  <textarea
                    readOnly
                    value={exportSessionData.session_string}
                    rows={6}
                    className="input-field text-xs font-mono bg-slate-950/60 leading-relaxed resize-none focus:ring-0 focus:border-slate-800"
                    onClick={(e) => e.target.select()}
                  />
                ) : (
                  <div className="p-4 rounded-xl bg-slate-950/60 text-center text-slate-500 text-sm border border-slate-800/50">
                    No active session found for this account.
                  </div>
                )}
              </div>

              {exportSessionData.session_string && (
                <div className="flex gap-2">
                  {/* Copy Button */}
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(exportSessionData.session_string);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="btn-primary text-xs flex-1 flex items-center justify-center gap-2"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 text-white" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        <span>Copy to Clipboard</span>
                      </>
                    )}
                  </button>

                  {/* Download Button */}
                  <button
                    onClick={() => {
                      const element = document.createElement("a");
                      const file = new Blob([exportSessionData.session_string], { type: 'text/plain' });
                      element.href = URL.createObjectURL(file);
                      element.download = `${exportSessionData.phone}.session`;
                      document.body.appendChild(element);
                      element.click();
                      document.body.removeChild(element);
                    }}
                    className="btn-secondary text-xs flex-1 flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download .session</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
