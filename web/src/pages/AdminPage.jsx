import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../auth';
import {
  Users,
  Smartphone,
  BarChart3,
  FileText,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Settings,
  Mail,
  Key,
} from 'lucide-react';

export default function AdminPage() {
  const { user, setUser } = useAuth();
  const [tab, setTab] = useState('stats');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const [emailForm, setEmailForm] = useState({
    newEmail: '',
    password: '',
    confirmPassword: '',
  });
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (tab === 'settings') {
      setEmailForm({
        newEmail: '',
        password: '',
        confirmPassword: '',
      });
      setErrorMsg('');
      setSuccessMsg('');
    }
  }, [tab]);

  useEffect(() => {
    loadTab(tab);
  }, [tab]);

  const loadTab = async (t) => {
    setLoading(true);
    try {
      switch (t) {
        case 'stats':
          setStats(await api.adminStats());
          break;
        case 'users':
          setUsers(await api.adminListUsers());
          break;
        case 'accounts':
          setAccounts(await api.adminListAccounts());
          break;
        case 'logs':
          setLogs(await api.adminAuditLogs(200));
          break;
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUser = async (userId, currentActive) => {
    try {
      await api.adminToggleUser(userId, !currentActive);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: !currentActive } : u))
      );
    } catch (err) {
      alert(err.message);
    }
  };

  const handleToggleAccount = async (accountId, currentActive) => {
    try {
      await api.adminToggleAccount(accountId, !currentActive);
      setAccounts((prev) =>
        prev.map((a) => (a.id === accountId ? { ...a, is_active: !currentActive } : a))
      );
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`Are you absolutely sure you want to delete user "${username}" and all their Telegram accounts/cached data? This action is irreversible.`)) return;
    try {
      await api.adminDeleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeleteAccount = async (accountId, phone) => {
    if (!confirm(`Are you absolutely sure you want to delete Telegram account "${phone}" and all its cached chats/messages? This action is irreversible.`)) return;
    try {
      await api.adminDeleteAccount(accountId);
      setAccounts((prev) => prev.filter((a) => a.id !== accountId));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const { newEmail, password, confirmPassword } = emailForm;

    if (!newEmail && !password) {
      setErrorMsg('Please specify a new email or password to update.');
      return;
    }

    if (newEmail) {
      if (newEmail.length < 5) {
        setErrorMsg('Email must be at least 5 characters long.');
        return;
      }
      if (!newEmail.includes('@')) {
        setErrorMsg('Please enter a valid email address.');
        return;
      }
    }

    if (password) {
      if (password.length < 6) {
        setErrorMsg('Password must be at least 6 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Passwords do not match.');
        return;
      }
    }

    setSaving(true);
    try {
      const updatedUser = await api.updateProfile(
        null, // username
        password || null,
        newEmail || null
      );
      setUser(updatedUser);
      setSuccessMsg('Profile updated successfully!');
      setEmailForm({
        newEmail: '',
        password: '',
        confirmPassword: '',
      });
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 'stats', label: 'Statistics', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'accounts', label: 'Accounts', icon: Smartphone },
    { id: 'logs', label: 'Audit Logs', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-3xl font-bold text-white">Admin Panel</h1>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-800/30 rounded-xl p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Stats */}
          {tab === 'stats' && stats && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: 'Total Users', value: stats.total_users, sub: `${stats.active_users} active` },
                { label: 'Telegram Accounts', value: stats.total_telegram_accounts, sub: `${stats.authorized_accounts} authorized` },
                { label: 'Chats', value: stats.total_chats, sub: `${stats.total_messages} messages` },
              ].map((s) => (
                <div key={s.label} className="stat-card">
                  <div className="stat-value">{s.value}</div>
                  <div className="stat-label">{s.label}</div>
                  <div className="text-xs text-slate-500">{s.sub}</div>
                </div>
              ))}
            </div>
          )}

          {/* Users */}
          {tab === 'users' && (
            <div className="glass-card overflow-hidden">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="text-slate-500">{u.id}</td>
                      <td className="font-medium text-slate-200">{u.username}</td>
                      <td className="text-slate-400">{u.email}</td>
                      <td>
                        <span className={`status-badge ${u.role === 'admin' ? 'status-authorized' : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${u.is_active ? 'status-authorized' : 'status-error'}`}>
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="text-xs text-slate-500">{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggleUser(u.id, u.is_active)}
                          className="p-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
                          title={u.is_active ? 'Disable User' : 'Enable User'}
                        >
                          {u.is_active ? (
                            <ToggleRight className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <ToggleLeft className="w-5 h-5 text-slate-500" />
                          )}
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u.id, u.username)}
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400/80 hover:text-red-400 transition-colors"
                          title="Delete User"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Accounts */}
          {tab === 'accounts' && (
            <div className="glass-card overflow-hidden">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Phone</th>
                    <th>Display Name</th>
                    <th>TG User ID</th>
                    <th>Owner ID</th>
                    <th>Status</th>
                    <th>Active</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td className="text-slate-500">{a.id}</td>
                      <td className="font-medium text-slate-200">{a.phone}</td>
                      <td className="text-slate-400">{a.display_name || '—'}</td>
                      <td className="text-slate-500 font-mono text-xs">{a.telegram_user_id || '—'}</td>
                      <td className="text-slate-500">{a.user_id}</td>
                      <td>
                        <span className={`status-badge status-${a.status}`}>{a.status}</span>
                      </td>
                      <td>
                        <span className={`status-badge ${a.is_active ? 'status-authorized' : 'status-error'}`}>
                          {a.is_active ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggleAccount(a.id, a.is_active)}
                          className="p-1.5 rounded-lg hover:bg-slate-800/50 transition-colors"
                          title={a.is_active ? 'Disable Account' : 'Enable Account'}
                        >
                          {a.is_active ? (
                            <ToggleRight className="w-5 h-5 text-emerald-400" />
                          ) : (
                            <ToggleLeft className="w-5 h-5 text-slate-500" />
                          )}
                        </button>
                        <button
                          onClick={() => handleDeleteAccount(a.id, a.phone)}
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400/80 hover:text-red-400 transition-colors"
                          title="Delete Account"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Audit Logs */}
          {tab === 'logs' && (
            <div className="glass-card overflow-hidden">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Target</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td className="text-xs text-slate-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="text-slate-400">{log.user_id ?? '—'}</td>
                      <td>
                        <code className="text-xs text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded">
                          {log.action}
                        </code>
                      </td>
                      <td className="text-xs text-slate-500">
                        {log.target_type ? `${log.target_type}#${log.target_id}` : '—'}
                      </td>
                      <td className="text-xs text-slate-600">{log.ip_address || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Settings */}
          {tab === 'settings' && (
            <div className="max-w-xl mx-auto glass-card p-6 md:p-8 animate-fade-in space-y-6">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Settings className="w-5 h-5 text-brand-400" />
                  Credentials Settings
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  Update your administrator email address and login password.
                </p>
              </div>

              {successMsg && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-medium animate-slide-in">
                  {successMsg}
                </div>
              )}

              {errorMsg && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium animate-slide-in">
                  {errorMsg}
                </div>
              )}

              <form onSubmit={handleUpdateProfile} className="space-y-4">
                {/* Current Email */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Current Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-3.5 w-5 h-5 text-slate-500" />
                    <input
                      type="text"
                      value={user?.email || ''}
                      disabled
                      className="input-field input-with-icon opacity-60 cursor-not-allowed bg-slate-950/40"
                    />
                  </div>
                </div>

                {/* New Email */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    New Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                    <input
                      type="email"
                      value={emailForm.newEmail}
                      onChange={(e) => setEmailForm({ ...emailForm, newEmail: e.target.value })}
                      placeholder="Enter new email address"
                      className="input-field input-with-icon"
                    />
                  </div>
                </div>

                {/* New Password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    New Password
                  </label>
                  <div className="relative">
                    <Key className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                    <input
                      type="password"
                      value={emailForm.password}
                      onChange={(e) => setEmailForm({ ...emailForm, password: e.target.value })}
                      placeholder="Minimum 6 characters"
                      className="input-field input-with-icon"
                    />
                  </div>
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Key className="absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
                    <input
                      type="password"
                      value={emailForm.confirmPassword}
                      onChange={(e) => setEmailForm({ ...emailForm, confirmPassword: e.target.value })}
                      placeholder="Confirm new password"
                      className="input-field input-with-icon"
                    />
                  </div>
                </div>

                {/* Submit button */}
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary w-full flex items-center justify-center gap-2 mt-6"
                >
                  {saving ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Saving Changes...</span>
                    </>
                  ) : (
                    <span>Save Changes</span>
                  )}
                </button>
              </form>
            </div>
          )}
        </>
      )}
    </div>
  );
}
