import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Key, User, Shield, Copy, RefreshCw, Check, Loader2, AlertCircle, QrCode, ShieldCheck, ShieldOff } from 'lucide-react';
import { useSearchParams } from 'react-router';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { useAuthStore } from '../../../stores/authStore';

// ── MFA state machine ────────────────────────────────────────────────────────
type MfaState = 'idle' | 'setting_up' | 'confirming' | 'disabling';

function MfaSetupPanel() {
  const [mfaState, setMfaState] = useState<MfaState>('idle');
  const [totpUri, setTotpUri]   = useState('');
  const [code, setCode]         = useState('');
  const [enabled, setEnabled]   = useState(false);

  const setupMutation = useMutation({
    mutationFn: doctorApi.mfaSetup,
    onSuccess: (data) => {
      setTotpUri(data.totp_uri);
      setMfaState('confirming');
    },
    onError: () => toast.error('Failed to start MFA setup'),
  });

  const confirmMutation = useMutation({
    mutationFn: () => doctorApi.mfaConfirm(code),
    onSuccess: () => {
      setEnabled(true);
      setMfaState('idle');
      setCode('');
      toast.success('MFA enabled — your account is now protected with TOTP');
    },
    onError: () => { toast.error('Invalid TOTP code — try again'); setCode(''); },
  });

  const disableMutation = useMutation({
    mutationFn: () => doctorApi.mfaDisable(code),
    onSuccess: () => {
      setEnabled(false);
      setMfaState('idle');
      setCode('');
      toast.success('MFA disabled');
    },
    onError: () => { toast.error('Invalid TOTP code — try again'); setCode(''); },
  });

  const qrUrl = totpUri
    ? `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(totpUri)}`
    : '';

  // ── Idle state ──────────────────────────────────────────────────────────────
  if (mfaState === 'idle') {
    return (
      <div className="pt-4 border-t border-[#E5E7EB]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-[#111827]">
              Two-Factor Authentication
            </p>
            <p className="text-xs text-[#6B7280] mt-0.5">
              {enabled
                ? 'Your account is protected with TOTP (Google Authenticator / Authy).'
                : 'Add an extra layer of security with TOTP authentication.'}
            </p>
          </div>
          {enabled ? (
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="flex items-center gap-1 text-xs text-[#15803d] font-medium">
                <ShieldCheck size={13} /> Enabled
              </span>
              <button
                onClick={() => { setCode(''); setMfaState('disabling'); }}
                className="h-8 px-3 rounded border border-[#FECACA] text-xs text-[#DC2626] hover:bg-[#FEF2F2] transition-colors"
              >
                Disable
              </button>
            </div>
          ) : (
            <button
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
              className="flex items-center gap-1.5 h-8 px-3 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151] hover:bg-[#F9FAFB] transition-colors disabled:opacity-50 flex-shrink-0"
            >
              {setupMutation.isPending
                ? <Loader2 size={12} className="animate-spin" />
                : <QrCode size={12} />}
              Enable MFA
            </button>
          )}
        </div>
      </div>
    );
  }

  // ── QR + confirm state ──────────────────────────────────────────────────────
  if (mfaState === 'confirming') {
    return (
      <div className="pt-4 border-t border-[#E5E7EB]">
        <p className="text-sm font-medium text-[#111827] mb-3">Scan with Authenticator App</p>
        <div className="flex gap-5 items-start flex-wrap">
          <div className="flex-shrink-0">
            <img
              src={qrUrl}
              alt="MFA QR code"
              width={180}
              height={180}
              className="rounded border border-[#E5E7EB] p-1 bg-white"
            />
            <p className="text-[10px] text-[#9CA3AF] mt-1 text-center">Scan with Google Authenticator</p>
          </div>
          <div className="flex-1 min-w-[200px]">
            <p className="text-xs text-[#6B7280] mb-3 leading-relaxed">
              1. Open Google Authenticator or Authy.<br />
              2. Scan the QR code on the left.<br />
              3. Enter the 6-digit code below to confirm.
            </p>
            <label htmlFor="totp-code-enable" className="block text-xs font-medium text-[#374151] mb-1.5">
              Verification Code
            </label>
            <input
              id="totp-code-enable"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              className="w-36 h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-base font-mono text-center text-[#111827] tracking-[0.3em] placeholder:text-[#D1D5DB] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => confirmMutation.mutate()}
                disabled={code.length !== 6 || confirmMutation.isPending}
                className="flex items-center gap-1.5 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
              >
                {confirmMutation.isPending
                  ? <Loader2 size={14} className="animate-spin" />
                  : <ShieldCheck size={14} />}
                Confirm & Enable
              </button>
              <button
                onClick={() => { setMfaState('idle'); setTotpUri(''); setCode(''); }}
                className="h-9 px-3 rounded border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Disable state ───────────────────────────────────────────────────────────
  return (
    <div className="pt-4 border-t border-[#E5E7EB]">
      <div className="flex items-center gap-2 mb-3">
        <ShieldOff size={16} className="text-[#DC2626]" />
        <p className="text-sm font-medium text-[#111827]">Disable Two-Factor Authentication</p>
      </div>
      <p className="text-xs text-[#6B7280] mb-3">
        Enter your current authenticator code to confirm.
      </p>
      <div className="flex items-end gap-2">
        <div>
          <label htmlFor="totp-code-disable" className="block text-xs font-medium text-[#374151] mb-1.5">Verification Code</label>
          <input
            id="totp-code-disable"
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            className="w-36 h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-base font-mono text-center text-[#111827] tracking-[0.3em] placeholder:text-[#D1D5DB] focus:outline-none focus:ring-2 focus:ring-[#DC2626]"
          />
        </div>
        <button
          onClick={() => disableMutation.mutate()}
          disabled={code.length !== 6 || disableMutation.isPending}
          className="h-10 px-4 rounded-md bg-[#DC2626] text-white text-sm hover:bg-[#B91C1C] transition-colors disabled:opacity-50 flex items-center gap-1.5"
        >
          {disableMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <ShieldOff size={14} />}
          Disable MFA
        </button>
        <button
          onClick={() => { setMfaState('idle'); setCode(''); }}
          className="h-10 px-3 rounded border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

type SettingsTab = 'profile' | 'codes' | 'security';

export function DoctorSettings() {
  const queryClient = useQueryClient();
  const doctorName = useAuthStore(s => s.user_name) ?? '';
  const [searchParams] = useSearchParams();
  const initialTab = (searchParams.get('tab') as SettingsTab) ?? 'profile';
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [copied, setCopied] = useState<string | null>(null);
  const [generateCount, setGenerateCount] = useState(5);
  const [expiresInDays, setExpiresInDays] = useState(30);

  // ── Codes query ──────────────────────────────────────────────────────────
  const { data: codes = [], isLoading: codesLoading, isError: codesError } = useQuery({
    queryKey: qk.codes(),
    queryFn: doctorApi.listCodes,
    enabled: activeTab === 'codes',
  });

  const generateMutation = useMutation({
    mutationFn: () => doctorApi.generateCodes(generateCount, expiresInDays),
    onSuccess: (newCodes) => {
      queryClient.invalidateQueries({ queryKey: qk.codes() });
      toast.success(`${newCodes.length} new codes generated`);
    },
    onError: () => toast.error('Failed to generate codes'),
  });

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(code);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  const available = codes.filter(c => !c.is_used).length;
  const used = codes.filter(c => c.is_used).length;

  const formatDate = (iso: string | null) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return iso;
    }
  };

  const tabs: { id: SettingsTab; label: string; icon: React.ReactNode }[] = [
    { id: 'profile',  label: 'Profile',             icon: <User size={15} />   },
    { id: 'codes',    label: 'Subscription Codes',  icon: <Key size={15} />    },
    { id: 'security', label: 'Security',            icon: <Shield size={15} /> },
  ];

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Settings</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">Manage your profile, codes, and security</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar nav */}
        <div className="w-44 flex-shrink-0">
          <nav className="flex flex-col gap-0.5">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2.5 h-9 px-3 rounded-md text-sm transition-colors text-left ${
                  activeTab === tab.id
                    ? 'bg-[#DCFCE7] text-[#1E7C45] font-medium'
                    : 'text-[#374151] hover:bg-[#F3F4F6]'
                }`}
              >
                <span className={activeTab === tab.id ? 'text-[#1E7C45]' : 'text-[#6B7280]'}>
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* ── Profile tab ─────────────────────────────────────── */}
          {activeTab === 'profile' && (
            <div className="bg-white border border-[#E5E7EB] rounded-lg p-6">
              <h2 className="text-base font-medium text-[#111827] mb-5">Profile Information</h2>
              <div className="max-w-md space-y-4">
                <div>
                  <label htmlFor="profile-name" className="block text-sm font-medium text-[#374151] mb-1.5">Full Name</label>
                  <input
                    id="profile-name"
                    defaultValue={doctorName}
                    className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                  />
                </div>
                <button
                  onClick={() => toast.info('Profile update coming soon')}
                  className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {/* ── Codes tab ───────────────────────────────────────── */}
          {activeTab === 'codes' && (
            <div className="space-y-5">
              {/* Stats + generate */}
              <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
                <h2 className="text-base font-medium text-[#111827] mb-4">Subscription Codes</h2>

                {codesLoading ? (
                  <div className="flex justify-center py-6">
                    <Loader2 size={20} className="animate-spin text-[#1E7C45]" />
                  </div>
                ) : codesError ? (
                  <div className="flex items-center gap-2 text-[#DC2626] text-sm py-4">
                    <AlertCircle size={16} />
                    Could not load codes
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-6 mb-5">
                      <div>
                        <p className="text-3xl font-bold text-[#1E7C45] tabular-nums">{available}</p>
                        <p className="text-sm text-[#6B7280]">Available</p>
                      </div>
                      <div>
                        <p className="text-3xl font-bold text-[#6B7280] tabular-nums">{used}</p>
                        <p className="text-sm text-[#6B7280]">Used</p>
                      </div>
                      <div>
                        <p className="text-3xl font-bold text-[#111827] tabular-nums">{codes.length}</p>
                        <p className="text-sm text-[#6B7280]">Total</p>
                      </div>
                    </div>

                    {/* Generate controls */}
                    <div className="flex items-center gap-3 p-3 bg-[#F9FAFB] rounded-lg border border-[#E5E7EB] flex-wrap">
                      <label htmlFor="codes-count" className="text-sm text-[#374151]">Generate:</label>
                      <select
                        id="codes-count"
                        value={generateCount}
                        onChange={e => setGenerateCount(Number(e.target.value))}
                        className="h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                      >
                        {[5, 10, 15, 20, 25].map(n => (
                          <option key={n} value={n}>{n} codes</option>
                        ))}
                      </select>
                      <label htmlFor="codes-expiry" className="text-sm text-[#374151]">Expires in:</label>
                      <select
                        id="codes-expiry"
                        value={expiresInDays}
                        onChange={e => setExpiresInDays(Number(e.target.value))}
                        className="h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                      >
                        {[30, 60, 90, 180, 365].map(n => (
                          <option key={n} value={n}>{n} days</option>
                        ))}
                      </select>
                      <button
                        onClick={() => generateMutation.mutate()}
                        disabled={generateMutation.isPending}
                        className="flex items-center gap-1.5 h-8 px-3 rounded bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
                      >
                        {generateMutation.isPending ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <RefreshCw size={13} />
                        )}
                        Generate
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Code list */}
              {!codesLoading && !codesError && codes.length > 0 && (
                <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
                  <div className="px-5 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB]">
                    <p className="text-sm font-medium text-[#111827]">All Codes ({codes.length})</p>
                  </div>
                  <div className="max-h-[480px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-white">
                        <tr className="border-b border-[#E5E7EB]">
                          {['Code', 'Status', 'Expires', 'Issued At', 'Used At', ''].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {codes.map(c => (
                          <tr key={c.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                            <td className="px-4 py-3">
                              <code className="text-sm font-mono text-[#374151]">{c.code}</code>
                            </td>
                            <td className="px-4 py-3">
                              {c.is_used ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-[#F3F4F6] text-[#6B7280]">
                                  Used
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-[#DCFCE7] text-[#15803d]">
                                  Available
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-[#6B7280]">
                              {formatDate(c.expires_at)}
                            </td>
                            <td className="px-4 py-3 text-sm text-[#6B7280]">
                              {formatDate(c.created_at)}
                            </td>
                            <td className="px-4 py-3 text-sm text-[#6B7280]">
                              {formatDate(c.used_at)}
                            </td>
                            <td className="px-4 py-3">
                              {!c.is_used && (
                                <button
                                  onClick={() => copyCode(c.code)}
                                  className="flex items-center gap-1 h-7 px-2 rounded border border-[#E5E7EB] text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] transition-colors"
                                >
                                  {copied === c.code ? (
                                    <Check size={11} className="text-[#1E7C45]" />
                                  ) : (
                                    <Copy size={11} />
                                  )}
                                  {copied === c.code ? 'Copied' : 'Copy'}
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Security tab ─────────────────────────────────────── */}
          {activeTab === 'security' && (
            <div className="bg-white border border-[#E5E7EB] rounded-lg p-6">
              <h2 className="text-base font-medium text-[#111827] mb-5">Security Settings</h2>
              <div className="max-w-md space-y-4">
                {[
                  { label: 'Current Password', placeholder: '••••••••' },
                  { label: 'New Password',     placeholder: '••••••••' },
                  { label: 'Confirm New Password', placeholder: '••••••••' },
                ].map(f => (
                  <div key={f.label}>
                    <label className="block text-sm font-medium text-[#374151] mb-1.5">{f.label}</label>
                    <input
                      type="password"
                      placeholder={f.placeholder}
                      className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                    />
                  </div>
                ))}
                <button
                  onClick={() => toast.info('Password change coming soon')}
                  className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
                >
                  Update Password
                </button>

                <MfaSetupPanel />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
