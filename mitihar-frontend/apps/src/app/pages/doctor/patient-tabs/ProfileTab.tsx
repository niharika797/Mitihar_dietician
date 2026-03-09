import React from 'react';
import { PatientSummary } from '../../../../lib/doctorApi';
import { Mail, Calendar, Target, AlertTriangle } from 'lucide-react';

interface ProfileTabProps {
  patient: PatientSummary;
}

function calcAge(dob: string | null): string {
  if (!dob) return '—';
  return String(Math.floor((Date.now() - new Date(dob).getTime()) / (1000 * 60 * 60 * 24 * 365.25)));
}

export function ProfileTab({ patient }: ProfileTabProps) {
  return (
    <div className="grid grid-cols-12 gap-5 max-w-4xl">
      {/* Personal Info */}
      <div className="col-span-12 md:col-span-6 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Personal Information</h3>
        <div className="space-y-3">
          <InfoRow label="Full Name" value={patient.name} />
          <InfoRow label="Age" value={patient.date_of_birth ? `${calcAge(patient.date_of_birth)} years` : '—'} />
          <InfoRow label="Gender" value={patient.gender === 'F' ? 'Female' : patient.gender === 'M' ? 'Male' : patient.gender} />
          <InfoRow label="Meals per Day" value={String(patient.meals_per_day)} />
          <div className="flex items-start gap-2 py-2">
            <Mail size={15} className="text-[#6B7280] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs text-[#9CA3AF]">Email</p>
              <p className="text-sm text-[#111827]">{patient.email}</p>
            </div>
          </div>
          {patient.date_of_birth && (
            <div className="flex items-start gap-2 py-2">
              <Calendar size={15} className="text-[#6B7280] mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs text-[#9CA3AF]">Date of Birth</p>
                <p className="text-sm text-[#111827]">{patient.date_of_birth}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Health Profile */}
      <div className="col-span-12 md:col-span-6 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Health Metrics</h3>
        <div className="space-y-3">
          <InfoRow
            label="BMI"
            value={patient.bmi != null ? patient.bmi.toFixed(1) : '—'}
          />
          <InfoRow
            label="BMR"
            value={patient.bmr != null ? `${Math.round(patient.bmr)} kcal/day` : '—'}
          />
          <InfoRow
            label="TDEE"
            value={patient.tdee != null ? `${Math.round(patient.tdee)} kcal/day` : '—'}
          />
        </div>
      </div>

      {/* Subscription */}
      <div className="col-span-12 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Subscription</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: 'Status',     value: patient.subscription_status.charAt(0).toUpperCase() + patient.subscription_status.slice(1) },
            { label: 'User Type',  value: patient.user_type === 'doctor_assigned' ? 'Doctor Assigned' : 'Standalone' },
            { label: 'Meals/Day',  value: String(patient.meals_per_day) },
          ].map(item => (
            <div key={item.label} className="bg-[#F9FAFB] rounded-lg p-3">
              <p className="text-xs text-[#9CA3AF] mb-1">{item.label}</p>
              <p className="text-sm font-medium text-[#111827]">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs text-[#9CA3AF]">{label}</span>
      <span className="text-sm text-[#111827] font-medium">{value}</span>
    </div>
  );
}
