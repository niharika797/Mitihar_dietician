import React, { useEffect, useCallback } from 'react';
import { Command } from 'cmdk';
import { Search, Users, ChefHat, LayoutDashboard, Bell, Settings, CreditCard } from 'lucide-react';
import { useNavigate } from 'react-router';
import { motion, useReducedMotion } from 'motion/react';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  role: 'doctor' | 'admin';
}

const doctorCommands = [
  { group: 'Navigation', icon: <LayoutDashboard size={15} />, label: 'Overview', to: '/doctor/overview' },
  { group: 'Navigation', icon: <Users size={15} />, label: 'Patients', to: '/doctor/patients' },
  { group: 'Navigation', icon: <Bell size={15} />, label: 'Requests', to: '/doctor/requests' },
  { group: 'Navigation', icon: <ChefHat size={15} />, label: 'Recipes', to: '/doctor/recipes' },
  { group: 'Navigation', icon: <Settings size={15} />, label: 'Settings', to: '/doctor/settings' },
  { group: 'Patients', icon: <Users size={15} />, label: 'Radha Sharma — Patient', to: '/doctor/patients/pat1' },
  { group: 'Patients', icon: <Users size={15} />, label: 'Meena Joshi — Patient', to: '/doctor/patients/pat2' },
  { group: 'Patients', icon: <Users size={15} />, label: 'Suresh Kumar — Patient', to: '/doctor/patients/pat3' },
  { group: 'Patients', icon: <Users size={15} />, label: 'Arjun Patel — Patient', to: '/doctor/patients/pat5' },
  { group: 'Actions', icon: <Bell size={15} />, label: 'View Pending Requests', to: '/doctor/requests' },
  { group: 'Actions', icon: <CreditCard size={15} />, label: 'Manage Subscription Codes', to: '/doctor/settings' },
];

const adminCommands = [
  { group: 'Navigation', icon: <LayoutDashboard size={15} />, label: 'Admin Overview', to: '/admin/overview' },
  { group: 'Navigation', icon: <Users size={15} />, label: 'Doctors', to: '/admin/doctors' },
  { group: 'Navigation', icon: <Users size={15} />, label: 'Patients', to: '/admin/patients' },
  { group: 'Navigation', icon: <ChefHat size={15} />, label: 'Food Database', to: '/admin/food-database' },
  { group: 'Navigation', icon: <CreditCard size={15} />, label: 'Codes & Billing', to: '/admin/billing' },
];

export function CommandPalette({ open, onClose, role }: CommandPaletteProps) {
  const navigate = useNavigate();
  const commands = role === 'doctor' ? doctorCommands : adminCommands;
  const prefersReducedMotion = useReducedMotion();

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (open) onClose();
      // parent handles opening
    }
    if (e.key === 'Escape') onClose();
  }, [open, onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (!open) return null;

  const groups = [...new Set(commands.map(c => c.group))];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      <motion.div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="button"
        aria-label="Close command palette"
        tabIndex={0}
        initial={prefersReducedMotion ? undefined : { opacity: 0 }}
        animate={prefersReducedMotion ? undefined : { opacity: 1 }}
        transition={{ duration: 0.15 }}
      />
      <motion.div
        className="relative w-full max-w-lg mx-4"
        initial={prefersReducedMotion ? undefined : { opacity: 0, scale: 0.98, y: -4 }}
        animate={prefersReducedMotion ? undefined : { opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
      >
        <Command
          className="bg-card rounded-xl border border-border shadow-[var(--shadow-modal)] overflow-hidden"
          shouldFilter
        >
          <div className="flex items-center gap-3 px-4 border-b border-border">
            <Search size={16} className="text-muted-foreground flex-shrink-0" />
            <Command.Input
              aria-label="Search patients, pages, and actions"
              placeholder="Search patients, pages, actions..."
              className="flex-1 h-12 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
            />
            <kbd className="flex items-center gap-0.5 rounded border border-border bg-input-background px-1.5 text-[10px] text-muted-foreground">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-72 overflow-y-auto py-2">
            <Command.Empty className="py-8 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>

            {groups.map(group => (
              <Command.Group key={group} heading={group}
                className="[&_[cmdk-group-heading]]:px-4 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-muted-foreground"
              >
                {commands.filter(c => c.group === group).map(cmd => (
                  <Command.Item
                    key={cmd.to}
                    value={cmd.label}
                    onSelect={() => { navigate(cmd.to); onClose(); }}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-secondary-foreground cursor-pointer data-[selected=true]:bg-brand-50 data-[selected=true]:text-primary transition-colors"
                  >
                    <span className="text-muted-foreground data-[selected=true]:text-primary">{cmd.icon}</span>
                    {cmd.label}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </motion.div>
    </div>
  );
}
