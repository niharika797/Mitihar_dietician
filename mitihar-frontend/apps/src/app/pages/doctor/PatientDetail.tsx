import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, AlertCircle, Loader2 } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ProfileTab } from './patient-tabs/ProfileTab';
import { PlanTab } from './patient-tabs/PlanTab';
import { ActivityTab } from './patient-tabs/ActivityTab';
import { NotesTab } from './patient-tabs/NotesTab';
import { VisitsTab } from './patient-tabs/VisitsTab';
import { MealConfigTab } from './patient-tabs/MealConfigTab';
import { WeeklySummaryTab } from './patient-tabs/WeeklySummaryTab';

type Tab = 'profile' | 'plan' | 'activity' | 'notes' | 'visits' | 'meal-config' | 'weekly-summary';

function subStatusToStatus(s: string): 'active' | 'inactive' | 'expired' | 'pending' {
  if (s === 'active') return 'active';
  if (s === 'expired') return 'expired';
  return 'inactive';
}

export function PatientDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  const patientId = Number(id);

  const { data: patient, isLoading, isError } = useQuery({
    queryKey: qk.patient(patientId),
    queryFn: () => doctorApi.getPatient(patientId),
    enabled: !isNaN(patientId),
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 size={28} className="animate-spin text-[#1E7C45]" />
      </div>
    );
  }

  if (isError || !patient) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle size={40} className="text-[#9CA3AF] mb-3" />
        <p className="text-base font-medium text-[#374151]">Patient not found</p>
        <button
          onClick={() => navigate('/doctor/patients')}
          className="mt-4 text-sm text-[#1E7C45] hover:underline"
        >
          ← Back to Patients
        </button>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'profile',        label: 'Profile'         },
    { id: 'plan',           label: 'Plan'            },
    { id: 'activity',       label: 'Activity'        },
    { id: 'notes',          label: 'Notes'           },
    { id: 'visits',         label: 'Visits'          },
    { id: 'meal-config',    label: 'Meal Config'     },
    { id: 'weekly-summary', label: 'Weekly Summary'  },
  ];

  return (
    <div>
      {/* Patient header */}
      <div className="bg-white border-b border-[#E5E7EB] px-6 py-4">
        <button
          onClick={() => navigate('/doctor/patients')}
          className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#374151] mb-3 transition-colors"
        >
          <ChevronLeft size={16} />
          Patients
        </button>

        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">{patient.name}</h1>
              <StatusBadge status={subStatusToStatus(patient.subscription_status)} />
            </div>
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-sm text-[#6B7280]">
              <span>{patient.gender}</span>
              {patient.bmi != null && (
                <>
                  <span className="text-[#D1D5DB]">·</span>
                  <span>BMI {patient.bmi.toFixed(1)}</span>
                </>
              )}
              {patient.tdee != null && (
                <>
                  <span className="text-[#D1D5DB]">·</span>
                  <span>TDEE {Math.round(patient.tdee)} kcal</span>
                </>
              )}
              <span className="text-[#D1D5DB]">·</span>
              <span>{patient.meals_per_day} meals/day</span>
            </div>
            <p className="text-sm text-[#6B7280] mt-0.5">{patient.email}</p>
          </div>

          <div className="text-right">
            <p className="text-xs text-[#9CA3AF]">
              {patient.user_type === 'doctor_assigned' ? 'Doctor assigned' : 'Standalone'}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-0 mt-4 -mb-4 border-b-0">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-[#1E7C45] text-[#1E7C45]'
                  : 'border-transparent text-[#6B7280] hover:text-[#374151] hover:border-[#D1D5DB]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="p-6">
        {activeTab === 'profile'     && <ProfileTab     patient={patient} />}
        {activeTab === 'plan'        && <PlanTab        patientId={patientId} patientTdee={patient.tdee ?? 2000} patientName={patient.name} patientDietType={patient.diet_type ?? 'Vegetarian'} patientMealsPerDay={patient.meals_per_day ?? 3} />}
        {activeTab === 'activity'    && <ActivityTab    patientId={patientId} patientName={patient.name} />}
        {activeTab === 'notes'       && <NotesTab       patientId={patientId} patientName={patient.name} />}
        {activeTab === 'visits'      && <VisitsTab      patientId={patientId} patientName={patient.name} />}
        {activeTab === 'meal-config'    && <MealConfigTab      patientId={patientId} />}
        {activeTab === 'weekly-summary' && <WeeklySummaryTab   patientId={patientId} />}
      </div>
    </div>
  );
}
