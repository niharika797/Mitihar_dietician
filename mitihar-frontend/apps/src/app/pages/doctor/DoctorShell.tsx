import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Sidebar } from '../../components/layout/Sidebar';
import { TopBar } from '../../components/layout/TopBar';
import { CommandPalette } from '../../components/layout/CommandPalette';
import { useAuthStore } from '../../../stores/authStore';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';

function getBreadcrumbs(pathname: string) {
  const map: Record<string, { label: string }[]> = {
    '/doctor/overview':  [{ label: 'Doctor' }, { label: 'Overview' }],
    '/doctor/patients':  [{ label: 'Doctor' }, { label: 'Patients' }],
    '/doctor/requests':  [{ label: 'Doctor' }, { label: 'Requests' }],
    '/doctor/recipes':   [{ label: 'Doctor' }, { label: 'Recipes' }],
    '/doctor/data-review': [{ label: 'Doctor' }, { label: 'Data Review' }],
    '/doctor/settings':  [{ label: 'Doctor' }, { label: 'Settings' }],
  };
  if (pathname.startsWith('/doctor/patients/')) {
    return [{ label: 'Doctor' }, { label: 'Patients' }, { label: 'Patient Detail' }];
  }
  return map[pathname] ?? [{ label: 'Doctor' }];
}

export function DoctorShell() {
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();

  const userName = useAuthStore(s => s.user_name) ?? 'Doctor';

  // Live pending request count for sidebar badge
  const { data: requests = [] } = useQuery({
    queryKey: qk.requests(),
    queryFn: doctorApi.listRequests,
    staleTime: 60 * 1000,
  });
  const pendingCount = requests.filter(r => r.status === 'pending').length;

  // Doctors have no push channel — the Doctor model carries no fcm_token and
  // every notify_* helper targets patients. So the header bell, which shipped
  // hardcoded to [], is the only place a patient's answer can reach the doctor.
  const { data: answered = [] } = useQuery({
    queryKey: qk.answeredFlaggedVisits,
    queryFn: () => doctorApi.getFlaggedVisits({ answeredOnly: true, limit: 10 }),
    staleTime: 60 * 1000,
    refetchOnWindowFocus: true,
  });

  const notifications = answered.map(f => ({
    id: String(f.id),
    text:
      f.status === 'approved'
        ? `${f.patient_name} confirmed the visit you flagged on ${new Date(f.visit_date).toLocaleDateString('en-IN')}`
        : `${f.patient_name} denied the visit you flagged on ${new Date(f.visit_date).toLocaleDateString('en-IN')}`,
    time: f.responded_at ? new Date(f.responded_at).toLocaleDateString('en-IN') : '',
    // No read/unread store exists, so nothing is marked read — showing them as
    // unread would leave a badge that can never be cleared.
    read: true,
    type: (f.status === 'approved' ? 'request' : 'warning') as 'request' | 'warning',
  }));

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
        role="doctor"
        userName={userName}
        userRole="Dietician"
        pendingCount={pendingCount}
      />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          breadcrumbs={getBreadcrumbs(location.pathname)}
          notifications={notifications}
          userName={userName}
          userRole="Dietician"
          onSearchOpen={() => setCmdOpen(true)}
        />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} role="doctor" />
    </div>
  );
}
