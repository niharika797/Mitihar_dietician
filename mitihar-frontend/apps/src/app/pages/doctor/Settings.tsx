import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { QRCodeSVG } from 'qrcode.react';
import { Key, User, Shield, Copy, RefreshCw, Check, Loader2, AlertCircle, QrCode, ShieldCheck, ShieldOff } from 'lucide-react';
import { useSearchParams } from 'react-router';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { useAuthStore } from '../../../stores/authStore';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';

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

  // ── Idle state ──────────────────────────────────────────────────────────────
  if (mfaState === 'idle') {
    return (
      <div className="pt-4 border-t border-border">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-foreground">
              Two-Factor Authentication
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {enabled
                ? 'Your account is protected with TOTP (Google Authenticator / Authy).'
                : 'Add an extra layer of security with TOTP authentication.'}
            </p>
          </div>
          {enabled ? (
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="flex items-center gap-1 text-xs text-brand-700 font-medium">
                <ShieldCheck size={14} /> Enabled
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setCode(''); setMfaState('disabling'); }}
                className="border-destructive/30 text-destructive hover:bg-red-50 hover:text-destructive"
              >
                Disable
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setupMutation.mutate()}
              disabled={setupMutation.isPending}
              className="flex-shrink-0"
            >
              {setupMutation.isPending
                ? <Loader2 size={14} className="animate-spin" />
                : <QrCode size={14} />}
              Enable MFA
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ── QR + confirm state ──────────────────────────────────────────────────────
  if (mfaState === 'confirming') {
    return (
      <div className="pt-4 border-t border-border">
        <p className="text-sm font-medium text-foreground mb-3">Scan with Authenticator App</p>
        <div className="flex gap-5 items-start flex-wrap">
          <div className="flex-shrink-0">
            <div
              role="img"
              aria-label="MFA QR code"
              className="rounded border border-border p-1 bg-card inline-block"
            >
              <QRCodeSVG value={totpUri} size={180} />
            </div>
            <p className="text-[10px] text-muted-foreground mt-1 text-center">Scan with Google Authenticator</p>
          </div>
          <div className="flex-1 min-w-[200px]">
            <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
              1. Open Google Authenticator or Authy.<br />
              2. Scan the QR code on the left.<br />
              3. Enter the 6-digit code below to confirm.
            </p>
            <label htmlFor="totp-code-enable" className="block text-xs font-medium text-secondary-foreground mb-1.5">
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
              className="w-36 h-10 px-3 rounded-md border border-border bg-input-background text-base font-mono text-center text-foreground tracking-[0.3em] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <div className="flex gap-2 mt-3">
              <Button
                variant="primary"
                size="md"
                onClick={() => confirmMutation.mutate()}
                disabled={code.length !== 6 || confirmMutation.isPending}
              >
                {confirmMutation.isPending
                  ? <Loader2 size={14} className="animate-spin" />
                  : <ShieldCheck size={14} />}
                Confirm & Enable
              </Button>
              <Button
                variant="outline"
                size="md"
                onClick={() => { setMfaState('idle'); setTotpUri(''); setCode(''); }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Disable state ───────────────────────────────────────────────────────────
  return (
    <div className="pt-4 border-t border-border">
      <div className="flex items-center gap-2 mb-3">
        <ShieldOff size={16} className="text-destructive" />
        <p className="text-sm font-medium text-foreground">Disable Two-Factor Authentication</p>
      </div>
      <p className="text-xs text-muted-foreground mb-3">
        Enter your current authenticator code to confirm.
      </p>
      <div className="flex items-end gap-2">
        <div>
          <label htmlFor="totp-code-disable" className="block text-xs font-medium text-secondary-foreground mb-1.5">Verification Code</label>
          <input
            id="totp-code-disable"
            type="text"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            className="w-36 h-10 px-3 rounded-md border border-border bg-input-background text-base font-mono text-center text-foreground tracking-[0.3em] placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-destructive"
          />
        </div>
        <Button
          variant="destructive"
          size="md"
          onClick={() => disableMutation.mutate()}
          disabled={code.length !== 6 || disableMutation.isPending}
        >
          {disableMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <ShieldOff size={14} />}
          Disable MFA
        </Button>
        <Button
          variant="outline"
          size="md"
          onClick={() => { setMfaState('idle'); setCode(''); }}
        >
          Cancel
        </Button>
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
    { id: 'profile',  label: 'Profile',             icon: <User size={16} />   },
    { id: 'codes',    label: 'Subscription Codes',  icon: <Key size={16} />    },
    { id: 'security', label: 'Security',            icon: <Shield size={16} /> },
  ];

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 data-tour="tour-settings" className="text-2xl font-semibold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage your profile, codes, and security</p>
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
                    ? 'bg-brand-100 text-primary font-medium'
                    : 'text-secondary-foreground hover:bg-accent'
                }`}
              >
                <span className={activeTab === tab.id ? 'text-primary' : 'text-muted-foreground'}>
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
            <Card className="p-6">
              <h2 className="text-base font-medium text-foreground mb-5">Profile Information</h2>
              <div className="max-w-md space-y-4">
                <div>
                  <label htmlFor="profile-name" className="block text-sm font-medium text-secondary-foreground mb-1.5">Full Name</label>
                  <input
                    id="profile-name"
                    defaultValue={doctorName}
                    className="w-full h-10 px-3 rounded-md border border-border bg-input-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  />
                </div>
                <Button variant="primary" size="md" onClick={() => toast.info('Profile update coming soon')}>
                  Save Changes
                </Button>
              </div>
            </Card>
          )}

          {/* ── Codes tab ───────────────────────────────────────── */}
          {activeTab === 'codes' && (
            <div className="space-y-5">
              {/* Stats + generate */}
              <Card className="p-5">
                <h2 className="text-base font-medium text-foreground mb-4">Subscription Codes</h2>

                {codesLoading ? (
                  <div className="flex justify-center py-6">
                    <Loader2 size={20} className="animate-spin text-primary" />
                  </div>
                ) : codesError ? (
                  <div className="flex items-center gap-2 text-destructive text-sm py-4">
                    <AlertCircle size={16} />
                    Could not load codes
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-6 mb-5">
                      <div>
                        <p className="text-3xl font-bold text-primary tabular-nums">{available}</p>
                        <p className="text-sm text-muted-foreground">Available</p>
                      </div>
                      <div>
                        <p className="text-3xl font-bold text-muted-foreground tabular-nums">{used}</p>
                        <p className="text-sm text-muted-foreground">Used</p>
                      </div>
                      <div>
                        <p className="text-3xl font-bold text-foreground tabular-nums">{codes.length}</p>
                        <p className="text-sm text-muted-foreground">Total</p>
                      </div>
                    </div>

                    {/* Generate controls */}
                    <div className="flex items-center gap-3 p-3 bg-input-background rounded-lg border border-border flex-wrap">
                      <label htmlFor="codes-count" className="text-sm text-secondary-foreground">Generate:</label>
                      <select
                        id="codes-count"
                        value={generateCount}
                        onChange={e => setGenerateCount(Number(e.target.value))}
                        className="h-8 px-2 rounded border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        {[5, 10, 15, 20, 25].map(n => (
                          <option key={n} value={n}>{n} codes</option>
                        ))}
                      </select>
                      <label htmlFor="codes-expiry" className="text-sm text-secondary-foreground">Expires in:</label>
                      <select
                        id="codes-expiry"
                        value={expiresInDays}
                        onChange={e => setExpiresInDays(Number(e.target.value))}
                        className="h-8 px-2 rounded border border-border bg-card text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        {[30, 60, 90, 180, 365].map(n => (
                          <option key={n} value={n}>{n} days</option>
                        ))}
                      </select>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => generateMutation.mutate()}
                        disabled={generateMutation.isPending}
                      >
                        {generateMutation.isPending ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <RefreshCw size={14} />
                        )}
                        Generate
                      </Button>
                    </div>
                  </>
                )}
              </Card>

              {/* Code list */}
              {!codesLoading && !codesError && codes.length > 0 && (
                <Card className="overflow-hidden">
                  <div className="px-5 py-3 bg-input-background border-b border-border">
                    <p className="text-sm font-medium text-foreground">All Codes ({codes.length})</p>
                  </div>
                  <div className="max-h-[480px] overflow-y-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b border-border">
                          {['Code', 'Status', 'Expires', 'Issued At', 'Used At', ''].map(h => (
                            <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {codes.map(c => (
                          <tr key={c.id} className="border-b border-border last:border-0 hover:bg-input-background">
                            <td className="px-4 py-3">
                              <code className="text-sm font-mono text-secondary-foreground">{c.code}</code>
                            </td>
                            <td className="px-4 py-3">
                              {c.is_used ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-muted text-muted-foreground">
                                  Used
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-brand-100 text-brand-700">
                                  Available
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {formatDate(c.expires_at)}
                            </td>
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {formatDate(c.created_at)}
                            </td>
                            <td className="px-4 py-3 text-sm text-muted-foreground">
                              {formatDate(c.used_at)}
                            </td>
                            <td className="px-4 py-3">
                              {!c.is_used && (
                                <Button variant="outline" size="sm" onClick={() => copyCode(c.code)}>
                                  {copied === c.code ? (
                                    <Check size={14} className="text-primary" />
                                  ) : (
                                    <Copy size={14} />
                                  )}
                                  {copied === c.code ? 'Copied' : 'Copy'}
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* ── Security tab ─────────────────────────────────────── */}
          {activeTab === 'security' && (
            <Card className="p-6">
              <h2 className="text-base font-medium text-foreground mb-5">Security Settings</h2>
              <div className="max-w-md space-y-4">
                {[
                  { label: 'Current Password', placeholder: '••••••••' },
                  { label: 'New Password',     placeholder: '••••••••' },
                  { label: 'Confirm New Password', placeholder: '••••••••' },
                ].map(f => (
                  <div key={f.label}>
                    <label className="block text-sm font-medium text-secondary-foreground mb-1.5">{f.label}</label>
                    <input
                      type="password"
                      placeholder={f.placeholder}
                      className="w-full h-10 px-3 rounded-md border border-border bg-input-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                    />
                  </div>
                ))}
                <Button variant="primary" size="md" onClick={() => toast.info('Password change coming soon')}>
                  Update Password
                </Button>

                <MfaSetupPanel />
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
