import React, { useState, useRef, useEffect } from 'react';
import { Search, Bell, Sun, Moon } from 'lucide-react';
import { Notification } from '../../data/mockData';
import { useTheme } from '../../hooks/useTheme';

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
  const notifRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useTheme();

  const unreadCount = notifications.filter(n => !n.read).length;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <header className="h-14 bg-card border-b border-border sticky top-0 z-40 flex items-center px-6 gap-4">
      {/* Breadcrumb */}
      <nav className="flex-1 flex items-center gap-1.5 text-sm">
        {breadcrumbs.map((crumb, i) => (
          <React.Fragment key={crumb.to ?? crumb.label}>
            {i > 0 && <span className="text-border">/</span>}
            <span className={i === breadcrumbs.length - 1 ? 'text-foreground font-medium' : 'text-muted-foreground'}>
              {crumb.label}
            </span>
          </React.Fragment>
        ))}
      </nav>

      {/* Search trigger */}
      <button
        onClick={onSearchOpen}
        className="hidden md:flex items-center gap-2 h-8 px-3 rounded-md border border-border bg-input-background text-muted-foreground text-sm hover:border-slate-300 transition-colors"
      >
        <Search size={14} />
        <span>Search...</span>
        <kbd className="ml-2 hidden lg:inline-flex items-center gap-1 rounded border border-border bg-card px-1.5 text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </button>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        className="relative w-9 h-9 rounded-md flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      {/* Notifications */}
      <div className="relative" ref={notifRef}>
        <button
          onClick={() => setNotifOpen(!notifOpen)}
          className="relative w-9 h-9 rounded-md flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-destructive text-destructive-foreground text-[9px] font-bold flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </button>

        {notifOpen && (
          <div className="absolute right-0 top-11 w-80 bg-card rounded-lg border border-border shadow-[var(--shadow-modal)] z-50 overflow-hidden">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs text-muted-foreground">{unreadCount} unread</span>
              )}
            </div>
            <div className="max-h-72 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">No notifications</p>
              ) : (
                notifications.map(notif => (
                  <div
                    key={notif.id}
                    className={`px-4 py-3 border-b border-border last:border-0 ${!notif.read ? 'bg-brand-50' : ''}`}
                  >
                    <div className="flex items-start gap-2">
                      <span className={`mt-1 flex-shrink-0 w-2 h-2 rounded-full ${
                        notif.type === 'alert' ? 'bg-destructive' :
                        notif.type === 'warning' ? 'bg-amber-500' : 'bg-primary'
                      }`} />
                      <div>
                        <p className="text-sm text-foreground">{notif.text}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{notif.time}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Avatar */}
      <div className="flex items-center gap-2 h-9 px-2">
        <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center">
          <span className="text-[11px] font-semibold text-primary">
            {userName.split(' ').map(w => w[0]).join('').slice(0, 2)}
          </span>
        </div>
        <span className="hidden md:block text-sm font-medium text-secondary-foreground">
          {userName.split(' ')[0]}
        </span>
      </div>
    </header>
  );
}
