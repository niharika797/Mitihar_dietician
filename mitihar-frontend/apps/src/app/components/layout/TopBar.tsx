import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, ChevronDown, User, Settings, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router';
import { logout } from '../../../lib/authService';
import { Notification } from '../../data/mockData';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface TopBarProps {
  breadcrumbs: BreadcrumbItem[];
  notifications: Notification[];
  userName: string;
  userRole: string;
  onSearchOpen?: () => void;
}

export function TopBar({ breadcrumbs, notifications, userName, userRole, onSearchOpen }: TopBarProps) {
  const [notifOpen, setNotifOpen] = useState(false);
  const [avatarOpen, setAvatarOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const avatarRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const unreadCount = notifications.filter(n => !n.read).length;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) setAvatarOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <header className="h-14 bg-white border-b border-[#E5E7EB] sticky top-0 z-40 flex items-center px-6 gap-4">
      {/* Breadcrumb */}
      <nav className="flex-1 flex items-center gap-1.5 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="text-[#D1D5DB]">/</span>}
            <span className={i === breadcrumbs.length - 1 ? 'text-[#111827] font-medium' : 'text-[#6B7280]'}>
              {crumb.label}
            </span>
          </React.Fragment>
        ))}
      </nav>

      {/* Search trigger */}
      <button
        onClick={onSearchOpen}
        className="hidden md:flex items-center gap-2 h-8 px-3 rounded-md border border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280] text-sm hover:border-[#D1D5DB] transition-colors"
      >
        <Search size={14} />
        <span>Search...</span>
        <kbd className="ml-2 hidden lg:inline-flex items-center gap-1 rounded border border-[#E5E7EB] bg-white px-1.5 text-[10px] text-[#9CA3AF]">
          ⌘K
        </kbd>
      </button>

      {/* Notifications */}
      <div className="relative" ref={notifRef}>
        <button
          onClick={() => setNotifOpen(!notifOpen)}
          className="relative w-9 h-9 rounded-md flex items-center justify-center text-[#6B7280] hover:bg-[#F3F4F6] transition-colors"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-[#DC2626] text-white text-[9px] font-bold flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </button>

        {notifOpen && (
          <div className="absolute right-0 top-11 w-80 bg-white rounded-lg border border-[#E5E7EB] shadow-[0_10px_25px_-5px_rgb(0_0_0/0.1)] z-50 overflow-hidden">
            <div className="px-4 py-3 border-b border-[#E5E7EB] flex items-center justify-between">
              <span className="text-sm font-semibold text-[#111827]">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs text-[#6B7280]">{unreadCount} unread</span>
              )}
            </div>
            <div className="max-h-72 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="text-sm text-[#6B7280] text-center py-6">No notifications</p>
              ) : (
                notifications.map(notif => (
                  <div
                    key={notif.id}
                    className={`px-4 py-3 border-b border-[#F3F4F6] last:border-0 ${!notif.read ? 'bg-[#F0FDF4]' : ''}`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`mt-1 flex-shrink-0 w-2 h-2 rounded-full ${
                        notif.type === 'alert' ? 'bg-[#DC2626]' :
                        notif.type === 'warning' ? 'bg-[#F59E0B]' : 'bg-[#1E7C45]'
                      }`} />
                      <div>
                        <p className="text-sm text-[#111827]">{notif.text}</p>
                        <p className="text-xs text-[#6B7280] mt-0.5">{notif.time}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Avatar dropdown */}
      <div className="relative" ref={avatarRef}>
        <button
          onClick={() => setAvatarOpen(!avatarOpen)}
          className="flex items-center gap-2 h-9 px-2 rounded-md hover:bg-[#F3F4F6] transition-colors"
        >
          <div className="w-7 h-7 rounded-full bg-[#DCFCE7] flex items-center justify-center">
            <span className="text-[11px] font-semibold text-[#1E7C45]">
              {userName.split(' ').map(w => w[0]).join('').slice(0, 2)}
            </span>
          </div>
          <span className="hidden md:block text-sm font-medium text-[#374151]">
            {userName.split(' ')[0]}
          </span>
          <ChevronDown size={14} className="text-[#9CA3AF]" />
        </button>

        {avatarOpen && (
          <div className="absolute right-0 top-11 w-52 bg-white rounded-lg border border-[#E5E7EB] shadow-[0_10px_25px_-5px_rgb(0_0_0/0.1)] z-50 overflow-hidden py-1">
            <div className="px-3 py-2.5 border-b border-[#F3F4F6]">
              <p className="text-sm font-medium text-[#111827]">{userName}</p>
              <p className="text-xs text-[#6B7280]">{userRole}</p>
            </div>
            <button className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors">
              <User size={15} className="text-[#6B7280]" />
              Profile
            </button>
            <button className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors">
              <Settings size={15} className="text-[#6B7280]" />
              Settings
            </button>
            <div className="border-t border-[#F3F4F6] mt-1 pt-1">
              <button
                onClick={() => { logout(); navigate('/'); }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#DC2626] hover:bg-[#FEF2F2] transition-colors"
              >
                <LogOut size={15} />
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
