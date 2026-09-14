import React from 'react';

type Status = 'active' | 'inactive' | 'pending' | 'expired' | 'approved' | 'rejected' | 'paid' | 'overdue' | 'warning';

interface StatusBadgeProps {
  status: Status;
  label?: string;
}

const statusStyles: Record<Status, string> = {
  active:   'bg-brand-100 text-brand-700',
  approved: 'bg-brand-100 text-brand-700',
  paid:     'bg-brand-100 text-brand-700',
  inactive: 'bg-slate-100 text-slate-600',
  pending:  'bg-amber-50 text-amber-500',
  expired:  'bg-red-50 text-red-600',
  rejected: 'bg-red-50 text-red-600',
  overdue:  'bg-red-50 text-red-600',
  warning:  'bg-amber-50 text-amber-500',
};

const defaultLabels: Record<Status, string> = {
  active:   'Active',
  approved: 'Approved',
  paid:     'Paid',
  inactive: 'Inactive',
  pending:  'Pending',
  expired:  'Expired',
  rejected: 'Rejected',
  overdue:  'Overdue',
  warning:  'Warning',
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status]}`}
    >
      {label ?? defaultLabels[status]}
    </span>
  );
}
