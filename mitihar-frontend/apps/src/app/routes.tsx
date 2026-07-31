import { createBrowserRouter, redirect } from 'react-router';
import { Login } from './pages/Login';
import { RequireAuth } from './components/auth/RequireAuth';
import { DoctorShell } from './pages/doctor/DoctorShell';
import { DoctorOverview } from './pages/doctor/Overview';
import { Patients } from './pages/doctor/Patients';
import { PatientDetail } from './pages/doctor/PatientDetail';
import { Requests } from './pages/doctor/Requests';
import { Recipes } from './pages/doctor/Recipes';
import { DataReview as DoctorDataReview } from './pages/doctor/DataReview';
import { DoctorSettings } from './pages/doctor/Settings';
import { AdminShell } from './pages/admin/AdminShell';
import { AdminOverview } from './pages/admin/AdminOverview';
import { AdminDoctors } from './pages/admin/AdminDoctors';
import { AdminPatients } from './pages/admin/AdminPatients';
import { FoodDatabase } from './pages/admin/FoodDatabase';
import { DataReview as AdminDataReview } from './pages/admin/DataReview';
import { AdminBilling } from './pages/admin/Billing';
import { AuditLogs } from './pages/admin/AuditLogs';
import { AdminSettings } from './pages/admin/AdminSettings';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Login,
  },

  // ── Doctor routes — protected by RequireAuth ──────────────────────────────
  {
    path: '/doctor',
    element: <RequireAuth allowedRole="doctor" />,
    children: [
      {
        Component: DoctorShell,
        children: [
          { index: true, loader: () => redirect('/doctor/overview') },
          { path: 'overview', Component: DoctorOverview },
          { path: 'patients', Component: Patients },
          { path: 'patients/:id', Component: PatientDetail },
          { path: 'requests', Component: Requests },
          { path: 'recipes', Component: Recipes },
          { path: 'data-review', Component: DoctorDataReview },
          { path: 'settings', Component: DoctorSettings },
        ],
      },
    ],
  },

  // ── Admin routes — protected by RequireAuth ───────────────────────────────
  {
    path: '/admin',
    element: <RequireAuth allowedRole="admin" />,
    children: [
      {
        Component: AdminShell,
        children: [
          { index: true, loader: () => redirect('/admin/overview') },
          { path: 'overview', Component: AdminOverview },
          { path: 'doctors', Component: AdminDoctors },
          { path: 'patients', Component: AdminPatients },
          { path: 'food-database', Component: FoodDatabase },
          { path: 'data-review', Component: AdminDataReview },
          { path: 'billing', Component: AdminBilling },
          { path: 'audit-logs', Component: AuditLogs },
          { path: 'settings', Component: AdminSettings },
        ],
      },
    ],
  },
]);
