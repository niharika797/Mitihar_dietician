import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Button } from './Button';
import { EASE_OUT } from '../../lib/motion-tokens';

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
  const prefersReducedMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <motion.div
            className="absolute inset-0 bg-black/40"
            onClick={onCancel}
            onKeyDown={(e) => e.key === "Escape" && onCancel()}
            role="button"
            aria-label="Close dialog"
            tabIndex={0}
            initial={prefersReducedMotion ? undefined : { opacity: 0 }}
            animate={prefersReducedMotion ? undefined : { opacity: 1 }}
            exit={prefersReducedMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
          <motion.div
            className="relative bg-card rounded-lg shadow-[var(--shadow-modal)] w-full max-w-[480px] mx-4 p-6"
            initial={prefersReducedMotion ? undefined : { opacity: 0, scale: 0.96 }}
            animate={prefersReducedMotion ? undefined : { opacity: 1, scale: 1 }}
            exit={prefersReducedMotion ? undefined : { opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
          >
            <div className="flex items-start gap-4">
              {variant === 'danger' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
                  <AlertTriangle size={20} className="text-red-600" />
                </div>
              )}
              <div className="flex-1">
                <h3 className="text-base font-semibold text-foreground mb-1">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 mt-6">
              <Button variant="outline" size="md" onClick={onCancel}>
                {cancelLabel}
              </Button>
              <Button
                variant={variant === 'danger' ? 'destructive' : 'primary'}
                size="md"
                onClick={onConfirm}
              >
                {confirmLabel}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
