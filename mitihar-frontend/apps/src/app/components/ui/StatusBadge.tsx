import React from 'react';

type Status = 'active' | 'inactive' | 'pending' | 'expired' | 'approved' | 'rejected' | 'paid' | 'overdue' | 'warning';

interface StatusBadgeProps {
  status: Status;
  label?: string;
}

const statusStyles: Record<Status, string> = {
  active:   'bg-[#DCFCE7] text-[#15803d]',
  approved: 'bg-[#DCFCE7] text-[#15803d]',
  paid:     'bg-[#DCFCE7] text-[#15803d]',
  inactive: 'bg-[#F3F4F6] text-[#4B5563]',
  pending:  'bg-[#FFFBEB] text-[#B45309]',
  expired:  'bg-[#FEF2F2] text-[#DC2626]',
  rejected: 'bg-[#FEF2F2] text-[#DC2626]',
  overdue:  'bg-[#FEF2F2] text-[#DC2626]',
  warning:  'bg-[#FFFBEB] text-[#B45309]',
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
