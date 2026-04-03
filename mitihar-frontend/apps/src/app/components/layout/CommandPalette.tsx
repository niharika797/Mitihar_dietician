import React, { useEffect, useCallback } from 'react';
import { Command } from 'cmdk';
import { Search, Users, ChefHat, LayoutDashboard, Bell, Settings, CreditCard } from 'lucide-react';
import { useNavigate } from 'react-router';

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
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} onKeyDown={(e) => e.key === "Escape" && onClose()} role="button" aria-label="Close command palette" tabIndex={0} />
      <div className="relative w-full max-w-lg mx-4">
        <Command
          className="bg-white rounded-xl border border-[#E5E7EB] shadow-[0_20px_25px_-5px_rgb(0_0_0/0.15)] overflow-hidden"
          shouldFilter
        >
          <div className="flex items-center gap-3 px-4 border-b border-[#E5E7EB]">
            <Search size={16} className="text-[#9CA3AF] flex-shrink-0" />
            <Command.Input
              aria-label="Search patients, pages, and actions"
              placeholder="Search patients, pages, actions..."
              className="flex-1 h-12 bg-transparent text-sm text-[#111827] placeholder:text-[#9CA3AF] outline-none"
            />
            <kbd className="flex items-center gap-0.5 rounded border border-[#E5E7EB] bg-[#F9FAFB] px-1.5 text-[10px] text-[#9CA3AF]">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-72 overflow-y-auto py-2">
            <Command.Empty className="py-8 text-center text-sm text-[#6B7280]">
              No results found.
            </Command.Empty>

            {groups.map(group => (
              <Command.Group key={group} heading={group}
                className="[&_[cmdk-group-heading]]:px-4 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-[#9CA3AF]"
              >
                {commands.filter(c => c.group === group).map(cmd => (
                  <Command.Item
                    key={cmd.to}
                    value={cmd.label}
                    onSelect={() => { navigate(cmd.to); onClose(); }}
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-[#374151] cursor-pointer data-[selected=true]:bg-[#F0FDF4] data-[selected=true]:text-[#1E7C45] transition-colors"
                  >
                    <span className="text-[#6B7280] data-[selected=true]:text-[#1E7C45]">{cmd.icon}</span>
                    {cmd.label}
                  </Command.Item>
                ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
