/**
 * RequireAuth — route guard component.
 *
 * Wraps protected route trees in routes.ts.
 * Reads Zustand auth state synchronously (no async, no flicker).
 *
 * Behaviour:
 *   - Not authenticated → redirect to /
 *   - Authenticated but wrong role → redirect to /
 *   - Authenticated + correct role → render <Outlet />
 */

import React from 'react';
import { Navigate, Outlet } from 'react-router';
import { useAuthStore, type UserRole } from '../../../stores/authStore';

interface RequireAuthProps {
  allowedRole: UserRole;
}

export function RequireAuth({ allowedRole }: RequireAuthProps) {
  const { is_authenticated, role } = useAuthStore();

  if (!is_authenticated) {
    return <Navigate to="/" replace />;
  }

  if (role !== allowedRole) {
    // Authenticated but wrong role (e.g. admin trying /doctor/*)
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
