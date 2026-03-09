import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Key, User, Shield, Copy, RefreshCw, Check, Loader2, AlertCircle } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { useAuthStore } from '../../../stores/authStore';

type SettingsTab = 'profile' | 'codes' | 'security';

export function DoctorSettings() {
  const queryClient = useQueryClient();
  const doctorName = useAuthStore(s => s.user_name) ?? '';
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
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
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">Full Name</label>
                  <input
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
                      <label className="text-sm text-[#374151]">Generate:</label>
                      <select
                        value={generateCount}
                        onChange={e => setGenerateCount(Number(e.target.value))}
                        className="h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                      >
                        {[5, 10, 15, 20, 25].map(n => (
                          <option key={n} value={n}>{n} codes</option>
                        ))}
                      </select>
                      <label className="text-sm text-[#374151]">Expires in:</label>
                      <select
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
                          {['Code', 'Status', 'Expires', 'Used At', ''].map(h => (
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

                <div className="pt-4 border-t border-[#E5E7EB]">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-[#111827]">Two-Factor Authentication</p>
                      <p className="text-xs text-[#6B7280]">Add an extra layer of security with TOTP</p>
                    </div>
                    <button
                      onClick={() => toast.info('MFA setup coming soon')}
                      className="h-8 px-3 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                    >
                      Enable MFA
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
