import React, { useState } from 'react';
import { currentAdmin } from '../../data/mockData';
import { toast } from 'sonner';
import { Shield, User } from 'lucide-react';

export function AdminSettings() {
  const [tab, setTab] = useState<'profile' | 'security'>('profile');

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Settings</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">Manage admin account and security settings</p>
      </div>

      <div className="flex gap-6">
        <div className="w-44 flex-shrink-0">
          <nav className="flex flex-col gap-0.5">
            {[
              { id: 'profile' as const, label: 'Profile', icon: <User size={15} /> },
              { id: 'security' as const, label: 'Security', icon: <Shield size={15} /> },
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2.5 h-9 px-3 rounded-md text-sm transition-colors ${
                  tab === t.id
                    ? 'bg-[#DCFCE7] text-[#1E7C45] font-medium'
                    : 'text-[#374151] hover:bg-[#F3F4F6]'
                }`}
              >
                <span className={tab === t.id ? 'text-[#1E7C45]' : 'text-[#6B7280]'}>{t.icon}</span>
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">
          {tab === 'profile' && (
            <div className="bg-white border border-[#E5E7EB] rounded-lg p-6">
              <h2 className="text-base font-medium text-[#111827] mb-5">Admin Profile</h2>
              <div className="max-w-md space-y-4">
                {[
                  { label: 'Full Name', value: currentAdmin.name },
                  { label: 'Email', value: currentAdmin.email },
                  { label: 'Role', value: currentAdmin.role },
                ].map(field => (
                  <div key={field.label}>
                    <label className="block text-sm font-medium text-[#374151] mb-1.5">{field.label}</label>
                    <input
                      defaultValue={field.value}
                      className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                    />
                  </div>
                ))}
                <button
                  onClick={() => toast.success('Profile updated')}
                  className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </div>
          )}

          {tab === 'security' && (
            <div className="bg-white border border-[#E5E7EB] rounded-lg p-6">
              <h2 className="text-base font-medium text-[#111827] mb-5">Security Settings</h2>
              <div className="max-w-md space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">Current Password</label>
                  <input type="password" placeholder="••••••••"
                    className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">New Password</label>
                  <input type="password" placeholder="••••••••"
                    className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
                </div>
                <button
                  onClick={() => toast.success('Password updated')}
                  className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
                >
                  Update Password
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
