import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { Sidebar } from '../../components/layout/Sidebar';
import { TopBar } from '../../components/layout/TopBar';
import { CommandPalette } from '../../components/layout/CommandPalette';
import { currentAdmin, adminNotifications, foodDatabase } from '../../data/mockData';

function getBreadcrumbs(pathname: string) {
  const map: Record<string, { label: string }[]> = {
    '/admin/overview':      [{ label: 'Admin' }, { label: 'Overview' }],
    '/admin/doctors':       [{ label: 'Admin' }, { label: 'Doctors' }],
    '/admin/patients':      [{ label: 'Admin' }, { label: 'Patients' }],
    '/admin/food-database': [{ label: 'Admin' }, { label: 'Food Database' }],
    '/admin/billing':       [{ label: 'Admin' }, { label: 'Codes & Billing' }],
    '/admin/audit-logs':    [{ label: 'Admin' }, { label: 'Audit Logs' }],
    '/admin/settings':      [{ label: 'Admin' }, { label: 'Settings' }],
  };
  return map[pathname] ?? [{ label: 'Admin' }];
}

export function AdminShell() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();

  const pendingFoodCount = foodDatabase.filter(f => f.status === 'pending').length;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(prev => !prev);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-[#F9FAFB]">
      <Sidebar
        role="admin"
        userName={currentAdmin.name}
        userRole={currentAdmin.role}
        pendingFoodCount={pendingFoodCount}
      />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          breadcrumbs={getBreadcrumbs(location.pathname)}
          notifications={adminNotifications}
          userName={currentAdmin.name}
          userRole={currentAdmin.role}
          onSearchOpen={() => setCmdOpen(true)}
        />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} role="admin" />
    </div>
  );
}
