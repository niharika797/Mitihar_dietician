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

const ACTIVITY_LABELS: Record<string, string> = {
  S: 'Sedentary',
  LA: 'Lightly Active',
  MA: 'Moderately Active',
  VA: 'Very Active',
  SA: 'Super Active',
};

export function ProfileTab({ patient }: ProfileTabProps) {
  return (
    <div className="grid grid-cols-12 gap-5 max-w-4xl">
      {/* Personal Info */}
      <div className="col-span-12 md:col-span-6 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Personal Information</h3>
        <div className="space-y-3">
          <InfoRow label="Full Name" value={patient.name} />
          <InfoRow label="Age" value={patient.date_of_birth ? `${calcAge(patient.date_of_birth)} years` : '—'} />
          <InfoRow label="Gender" value={patient.gender ? patient.gender.charAt(0).toUpperCase() + patient.gender.slice(1).toLowerCase() : '—'} />
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
          <InfoRow label="Height" value={patient.height_cm ? `${patient.height_cm} cm` : '—'} />
          <InfoRow label="Current Weight" value={patient.weight_kg ? `${patient.weight_kg} kg` : '—'} />
          <InfoRow label="Target Weight" value={patient.target_weight_kg ? `${patient.target_weight_kg} kg` : '—'} />
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
          <InfoRow label="Activity Level" value={ACTIVITY_LABELS[patient.activity_level ?? ''] ?? patient.activity_level ?? '—'} />
        </div>
      </div>

      {/* Dietary & Goals */}
      <div className="col-span-12 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Dietary & Health Profile</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div>
            <p className="text-xs text-[#9CA3AF] mb-1">Diet Type</p>
            <p className="text-sm font-medium text-[#111827]">{patient.diet_type || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-[#9CA3AF] mb-1">Main Health Condition</p>
            <p className="text-sm font-medium text-[#111827]">{patient.health_condition || '—'}</p>
          </div>
          <div className="col-span-1 md:col-span-2 border-t border-[#F3F4F6] pt-4">
            <p className="text-xs text-[#9CA3AF] mb-2 uppercase tracking-wider font-semibold">Health Goals</p>
            <div className="flex flex-wrap gap-2">
              {patient.health_goals.length > 0 ? (
                patient.health_goals.map(goal => (
                  <span key={goal} className="px-2.5 py-1 bg-[#F0FDF4] text-[#166534] text-xs font-medium rounded-full border border-[#BBF7D0]">
                    {goal}
                  </span>
                ))
              ) : (
                <span className="text-sm text-[#9CA3AF]">No specific goals listed</span>
              )}
            </div>
          </div>
          <div className="col-span-1 md:col-span-2 border-t border-[#F3F4F6] pt-4">
            <p className="text-xs text-[#9CA3AF] mb-2 uppercase tracking-wider font-semibold flex items-center gap-1">
              <AlertTriangle size={12} className="text-[#DC2626]" /> Medical Conditions & Allergies
            </p>
            <div className="space-y-3">
              <div>
                <p className="text-[10px] text-[#9CA3AF] mb-1 italic">Conditions:</p>
                <div className="flex flex-wrap gap-2">
                  {patient.medical_conditions.length > 0 ? (
                    patient.medical_conditions.map(cond => (
                      <span key={cond} className="px-2.5 py-1 bg-[#FEF2F2] text-[#991B1B] text-xs font-medium rounded-full border border-[#FECACA]">
                        {cond}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-[#9CA3AF]">None reported</span>
                  )}
                </div>
              </div>
              <div>
                <p className="text-[10px] text-[#9CA3AF] mb-1 italic">Allergies:</p>
                <div className="flex flex-wrap gap-2">
                  {patient.food_allergies.length > 0 ? (
                    patient.food_allergies.map(allergy => (
                      <span key={allergy} className="px-2.5 py-1 bg-[#FFFBEB] text-[#92400E] text-xs font-medium rounded-full border border-[#FEF3C7]">
                        {allergy}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-[#9CA3AF]">No food allergies reported</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Subscription */}
      <div className="col-span-12 bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Subscription Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: 'Status',     value: patient.subscription_status.charAt(0).toUpperCase() + patient.subscription_status.slice(1) },
            { label: 'User Type',  value: patient.user_type === 'doctor_assigned' ? 'Doctor Assigned' : 'Standalone' },
            { label: 'Meals Intake',  value: `${patient.meals_per_day} meals/day` },
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
