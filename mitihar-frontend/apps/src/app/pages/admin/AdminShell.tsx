import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Sidebar } from '../../components/layout/Sidebar';
import { TopBar } from '../../components/layout/TopBar';
import { CommandPalette } from '../../components/layout/CommandPalette';
import { useAuthStore } from '../../../stores/authStore';
import { adminApi } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

function getBreadcrumbs(pathname: string) {
  const map: Record<string, { label: string }[]> = {
    '/admin/overview':      [{ label: 'Admin' }, { label: 'Overview' }],
    '/admin/doctors':       [{ label: 'Admin' }, { label: 'Doctors' }],
    '/admin/patients':      [{ label: 'Admin' }, { label: 'Patients' }],
    '/admin/food-database': [{ label: 'Admin' }, { label: 'Food Database' }],
    '/admin/billing':       [{ label: 'Admin' }, { label: 'Codes & Consultations' }],
    '/admin/audit-logs':    [{ label: 'Admin' }, { label: 'Audit Logs' }],
    '/admin/settings':      [{ label: 'Admin' }, { label: 'Settings' }],
  };
  return map[pathname] ?? [{ label: 'Admin' }];
}

export function AdminShell() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();
  const { user_name } = useAuthStore();

  // Pending food badge — count doctor-submitted unverified items
  const { data: pendingFoodItems = [] } = useQuery({
    queryKey: aqk.pendingFood(),
    queryFn: () => adminApi.listFood({ source: 'doctor', is_verified: false, page_size: 100 }),
    staleTime: 3 * 60 * 1000,
  });
  const pendingFoodCount = pendingFoodItems.length;

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

  const adminName  = user_name ?? 'Admin';
  const adminRole  = 'admin';

  return (
    <div className="flex h-screen overflow-hidden bg-[#F9FAFB]">
      <Sidebar
        role="admin"
        userName={adminName}
        userRole={adminRole}
        pendingFoodCount={pendingFoodCount}
      />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          breadcrumbs={getBreadcrumbs(location.pathname)}
          notifications={[]}
          userName={adminName}
          userRole={adminRole}
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
