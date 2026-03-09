import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onCancel} />
      <div
        className="relative bg-white rounded-lg shadow-[0_20px_25px_-5px_rgb(0_0_0/0.1)] w-full max-w-[480px] mx-4 p-6"
      >
        <div className="flex items-start gap-4">
          {variant === 'danger' && (
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#FEF2F2] flex items-center justify-center">
              <AlertTriangle size={20} className="text-[#DC2626]" />
            </div>
          )}
          <div className="flex-1">
            <h3 className="text-base font-semibold text-[#111827] mb-1">{title}</h3>
            <p className="text-sm text-[#6B7280]">{description}</p>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] text-sm transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`h-9 px-4 rounded-md text-white text-sm transition-colors ${
              variant === 'danger'
                ? 'bg-[#DC2626] hover:bg-[#B91C1C]'
                : 'bg-[#1E7C45] hover:bg-[#166534]'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
