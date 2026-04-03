import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router';
import { logout } from '../../../lib/authService';
import {
  LayoutDashboard, Users, Bell, ChefHat, Settings, LogOut,
  Stethoscope, Utensils, CreditCard, ScrollText, ChevronLeft, ChevronRight,
  Leaf,
} from 'lucide-react';

type Role = 'doctor' | 'admin';

interface NavItem {
  icon: React.ReactNode;
  label: string;
  to: string;
  badge?: number;
}

interface NavSection {
  label?: string;
  items: NavItem[];
}

interface SidebarProps {
  role: Role;
  userName: string;
  userRole: string;
  pendingCount?: number;
  pendingFoodCount?: number;
}

const STORAGE_KEY = 'mityahar_sidebar_collapsed';

export function Sidebar({ role, userName, userRole, pendingCount = 0, pendingFoodCount = 0 }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === 'true'; } catch { return false; }
  });
  const navigate = useNavigate();

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, String(collapsed)); } catch {}
  }, [collapsed]);

  const doctorSections: NavSection[] = [
    {
      label: 'MAIN',
      items: [
        { icon: <LayoutDashboard size={18} />, label: 'Overview', to: '/doctor/overview' },
        { icon: <Users size={18} />, label: 'Patients', to: '/doctor/patients' },
        { icon: <Bell size={18} />, label: 'Requests', to: '/doctor/requests', badge: pendingCount },
        { icon: <ChefHat size={18} />, label: 'Recipes', to: '/doctor/recipes' },
      ],
    },
    {
      label: 'ACCOUNT',
      items: [
        { icon: <Settings size={18} />, label: 'Settings', to: '/doctor/settings' },
      ],
    },
  ];

  const adminSections: NavSection[] = [
    {
      label: 'OVERVIEW',
      items: [
        { icon: <LayoutDashboard size={18} />, label: 'Overview', to: '/admin/overview' },
      ],
    },
    {
      label: 'PLATFORM',
      items: [
        { icon: <Stethoscope size={18} />, label: 'Doctors', to: '/admin/doctors' },
        { icon: <Users size={18} />, label: 'Patients', to: '/admin/patients' },
        { icon: <Utensils size={18} />, label: 'Food Database', to: '/admin/food-database', badge: pendingFoodCount },
      ],
    },
    {
      label: 'CONSULTATIONS',
      items: [
        { icon: <CreditCard size={18} />, label: 'Codes & Consultations', to: '/admin/billing' },
      ],
    },
    {
      label: 'AUDIT',
      items: [
        { icon: <ScrollText size={18} />, label: 'Audit Logs', to: '/admin/audit-logs' },
      ],
    },
    {
      label: 'ACCOUNT',
      items: [
        { icon: <Settings size={18} />, label: 'Settings', to: '/admin/settings' },
      ],
    },
  ];

  const sections = role === 'doctor' ? doctorSections : adminSections;

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <aside
      className="relative flex flex-col bg-white border-r border-[#E5E7EB] h-screen flex-shrink-0 transition-all duration-200"
      style={{ width: collapsed ? 64 : 240 }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-[#E5E7EB] flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-[#1E7C45] flex items-center justify-center flex-shrink-0">
          <Leaf size={16} className="text-white" />
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-[#111827] tracking-tight">Mitihar</span>
        )}
      </div>

      {/* Nav sections */}
      <div className="flex-1 overflow-y-auto py-4 px-2 flex flex-col gap-5">
        {sections.map((section, si) => (
          <div key={si}>
            {!collapsed && section.label && (
              <p className="text-[10px] font-medium uppercase tracking-widest text-[#9CA3AF] px-2 mb-1.5">
                {section.label}
              </p>
            )}
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    `relative flex items-center gap-3 rounded-md px-2 h-11 text-sm transition-colors group
                    ${isActive
                      ? 'bg-[#DCFCE7] text-[#1E7C45] font-medium'
                      : 'text-[#374151] hover:bg-[#F3F4F6]'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-[#1E7C45] rounded-r" />
                      )}
                      <span className={`flex-shrink-0 ${isActive ? 'text-[#1E7C45]' : 'text-[#6B7280] group-hover:text-[#374151]'}`}>
                        {item.icon}
                      </span>
                      {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                      {!collapsed && item.badge != null && item.badge > 0 && (
                        <span className="ml-auto flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-[#1E7C45] text-white text-[10px] font-semibold">
                          {item.badge}
                        </span>
                      )}
                      {collapsed && item.badge != null && item.badge > 0 && (
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#DC2626]" />
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom: user + logout */}
      <div className="border-t border-[#E5E7EB] p-3 flex flex-col gap-1 flex-shrink-0">
        {!collapsed && (
          <div className="flex items-center gap-2.5 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-[#DCFCE7] flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-[#1E7C45]">
                {userName.split(' ').map(w => w[0]).join('').slice(0, 2)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[#111827] truncate">{userName}</p>
              <p className="text-[10px] text-[#6B7280] truncate">{userRole}</p>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          title={collapsed ? 'Logout' : undefined}
          className="flex items-center gap-3 rounded-md px-2 h-9 text-sm text-[#6B7280] hover:bg-[#FEF2F2] hover:text-[#DC2626] transition-colors w-full"
        >
          <LogOut size={16} className="flex-shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-[72px] w-6 h-6 rounded-full bg-white border border-[#E5E7EB] shadow-sm flex items-center justify-center hover:border-[#1E7C45] transition-colors z-10"
      >
        {collapsed
          ? <ChevronRight size={12} className="text-[#6B7280]" />
          : <ChevronLeft size={12} className="text-[#6B7280]" />
        }
      </button>
    </aside>
  );
}
