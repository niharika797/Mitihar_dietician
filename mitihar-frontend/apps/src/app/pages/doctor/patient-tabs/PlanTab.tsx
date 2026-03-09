import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { doctorApi, MealEntry } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import {
  MoreHorizontal, StickyNote, Flame, Beef, Wheat, Droplets,
  Plus, X, Loader2, AlertCircle, CalendarDays,
} from 'lucide-react';

interface PlanTabProps {
  patientId: number;
  patientTdee: number;
  patientName: string;
}

interface CustomMealForm {
  name: string;
  mealType: string;
  calories: string;
  protein: string;
  carbs: string;
  fat: string;
  cuisine: string;
  saveToLibrary: boolean;
}

const EMPTY_FORM: CustomMealForm = {
  name: '', mealType: 'Breakfast', calories: '', protein: '',
  carbs: '', fat: '', cuisine: '', saveToLibrary: false,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Group meals by their Date field */
function groupByDate(meals: MealEntry[]): Record<string, MealEntry[]> {
  return meals.reduce((acc, m) => {
    const d = m.Date ?? 'Unknown';
    if (!acc[d]) acc[d] = [];
    acc[d].push(m);
    return acc;
  }, {} as Record<string, MealEntry[]>);
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  } catch {
    return dateStr;
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MacroPill({ icon, value, unit, color }: { icon: React.ReactNode; value: number; unit: string; color: string }) {
  return (
    <span className={`flex items-center gap-1 text-xs ${color}`}>
      {icon}
      <span className="tabular-nums font-medium">{Math.round(value)}</span>
      <span className="text-[#9CA3AF]">{unit}</span>
    </span>
  );
}

function MealCard({ meal }: { meal: MealEntry }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 group relative hover:border-[#D1D5DB] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div>
          <span className="text-xs font-medium uppercase tracking-wide text-[#6B7280]">
            {meal['Meal Type']}
          </span>
          <p className="text-xs text-[#9CA3AF]">{meal['Diet Type']}</p>
        </div>
        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] opacity-0 group-hover:opacity-100 hover:bg-[#F3F4F6] hover:text-[#374151] transition-all"
          >
            <MoreHorizontal size={15} />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-8 z-20 w-36 bg-white rounded-lg border border-[#E5E7EB] shadow-[0_10px_25px_-5px_rgb(0_0_0/0.1)] py-1">
                <button
                  onClick={() => setMenuOpen(false)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                >
                  <StickyNote size={13} className="text-[#6B7280]" />
                  Add note
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <p className="text-sm font-medium text-[#111827] mb-3 leading-snug">{meal['Menu Names']}</p>

      <div className="flex items-center gap-3 flex-wrap">
        <MacroPill icon={<Flame size={11} />}   value={meal['Total Calories']} unit="kcal" color="text-[#DC2626]" />
        <MacroPill icon={<Beef size={11} />}    value={meal['Total Protein']}  unit="g P"  color="text-[#2563EB]" />
        <MacroPill icon={<Wheat size={11} />}   value={meal['Total Carbs']}    unit="g C"  color="text-[#F59E0B]" />
        <MacroPill icon={<Droplets size={11} />} value={meal['Total Fat']}     unit="g F"  color="text-[#6B7280]" />
      </div>

      {meal.doctor_note && (
        <div className="mt-3 px-3 py-2 bg-[#F0FDF4] rounded-md border border-[#DCFCE7]">
          <p className="text-xs text-[#15803d] flex items-start gap-1.5">
            <StickyNote size={11} className="mt-0.5 flex-shrink-0" />
            <span>{meal.doctor_note}</span>
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function PlanTab({ patientId, patientTdee, patientName }: PlanTabProps) {
  const [activeDateIdx, setActiveDateIdx] = useState(0);
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState<CustomMealForm>(EMPTY_FORM);
  const [addSuccess, setAddSuccess] = useState(false);

  const { data: plan, isLoading, isError } = useQuery({
    queryKey: qk.patientPlan(patientId),
    queryFn: () => doctorApi.getPatientPlan(patientId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
      </div>
    );
  }

  if (isError || !plan) {
    return (
      <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
        <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
        <p className="text-base font-medium text-[#374151]">No active plan</p>
        <p className="text-sm text-[#6B7280] mt-1">
          {patientName} doesn't have an active meal plan yet.
        </p>
      </div>
    );
  }

  const grouped = groupByDate(plan.meals);
  const dates = Object.keys(grouped).sort();

  if (dates.length === 0) {
    return (
      <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
        <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
        <p className="text-base font-medium text-[#374151]">Plan has no meals yet</p>
      </div>
    );
  }

  const activeDate = dates[activeDateIdx] ?? dates[0];
  const dayMeals = grouped[activeDate] ?? [];

  const totalCalories = dayMeals.reduce((s, m) => s + (m['Total Calories'] ?? 0), 0);
  const totalProtein  = dayMeals.reduce((s, m) => s + (m['Total Protein']  ?? 0), 0);
  const totalCarbs    = dayMeals.reduce((s, m) => s + (m['Total Carbs']    ?? 0), 0);
  const totalFat      = dayMeals.reduce((s, m) => s + (m['Total Fat']      ?? 0), 0);

  const handleAddMeal = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: wire to POST /api/v1/doctor/recipes with save_to_library flag
    // payload: { ...form, patient_id: patientId, save_to_library: form.saveToLibrary }
    console.log('Custom meal submitted:', { patientId, ...form });
    setAddSuccess(true);
    setTimeout(() => {
      setAddSuccess(false);
      setShowAddForm(false);
      setForm(EMPTY_FORM);
    }, 1500);
  };

  const field = (key: keyof CustomMealForm, label: string, type = 'text', placeholder = '') => (
    <div key={key}>
      <label className="block text-xs font-medium text-[#374151] mb-1">{label}</label>
      <input
        required={type === 'number'}
        type={type}
        min={type === 'number' ? 0 : undefined}
        value={form[key] as string}
        onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
      />
    </div>
  );

  return (
    <div className="max-w-4xl">
      {/* Doctor notes banner */}
      {plan.doctor_notes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <p className="text-xs font-medium text-[#15803d] mb-0.5">Doctor Notes</p>
          <p className="text-sm text-[#374151]">{plan.doctor_notes}</p>
        </div>
      )}

      {/* Day selector strip */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        {dates.map((date, idx) => (
          <button
            key={date}
            onClick={() => setActiveDateIdx(idx)}
            className={`h-8 px-3 text-sm font-medium rounded-md transition-colors ${
              activeDateIdx === idx
                ? 'bg-[#1E7C45] text-white'
                : 'bg-white border border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:text-[#374151]'
            }`}
          >
            {formatDate(date)}
          </button>
        ))}
      </div>

      {/* Heading + daily totals */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#111827]">{activeDate} — Meal Plan</h2>
          <p className="text-sm text-[#6B7280]">{dayMeals.length} meals planned</p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-[#6B7280]">Day total:</span>
          <span className="font-semibold text-[#111827] tabular-nums">{Math.round(totalCalories)} kcal</span>
          <span className="text-xs text-[#9CA3AF]">
            P:{Math.round(totalProtein)}g · C:{Math.round(totalCarbs)}g · F:{Math.round(totalFat)}g
          </span>
        </div>
      </div>

      {/* TDEE comparison bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-[#374151]">Calories vs TDEE</span>
          <span className="text-sm text-[#6B7280] tabular-nums">
            {Math.round(totalCalories)} / {Math.round(patientTdee)} kcal
          </span>
        </div>
        <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#1E7C45] rounded-full transition-all"
            style={{ width: `${Math.min(100, (totalCalories / patientTdee) * 100)}%` }}
          />
        </div>
        <p className="text-xs text-[#6B7280] mt-1.5">
          {totalCalories < patientTdee
            ? `${Math.round(patientTdee - totalCalories)} kcal below TDEE (deficit plan)`
            : `${Math.round(totalCalories - patientTdee)} kcal above TDEE`}
        </p>
      </div>

      {/* Meal cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {dayMeals.map((meal, i) => (
          <MealCard key={i} meal={meal} />
        ))}
      </div>

      {/* Add Custom Meal */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 h-9 px-4 rounded-md border border-dashed border-[#D1D5DB] text-sm text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] transition-colors w-full justify-center"
        >
          <Plus size={14} />
          Add Custom Meal to {activeDate}
        </button>
      ) : (
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#111827]">Add Custom Meal — {activeDate}</h3>
            <button
              onClick={() => { setShowAddForm(false); setForm(EMPTY_FORM); }}
              className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#374151] transition-colors"
            >
              <X size={15} />
            </button>
          </div>

          <form onSubmit={handleAddMeal}>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-[#374151] mb-1">
                  Recipe Name <span className="text-[#DC2626]">*</span>
                </label>
                <input
                  required
                  type="text"
                  value={form.name}
                  onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. Masoor Dal Soup"
                  className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#374151] mb-1">Meal Type</label>
                <select
                  value={form.mealType}
                  onChange={e => setForm(p => ({ ...p, mealType: e.target.value }))}
                  className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                >
                  {['Breakfast', 'MorningSnacks', 'Lunch', 'EveningSnacks', 'Dinner'].map(t => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>

              {field('cuisine',  'Cuisine',         'text',   'e.g. South Indian')}
              {field('calories', 'Calories (kcal) *', 'number', '0')}
              {field('protein',  'Protein (g) *',     'number', '0')}
              {field('carbs',    'Carbs (g) *',       'number', '0')}
              {field('fat',      'Fat (g) *',         'number', '0')}
            </div>

            {/* Scope checkboxes */}
            <div className="border border-[#E5E7EB] rounded-md p-3 mb-4 bg-[#F9FAFB] flex flex-col gap-2.5">
              <label className="flex items-start gap-2.5 cursor-not-allowed opacity-70">
                <input type="checkbox" checked disabled readOnly className="mt-0.5 accent-[#1E7C45]" />
                <div>
                  <p className="text-sm font-medium text-[#374151]">Add to this patient's plan</p>
                  <p className="text-xs text-[#9CA3AF]">Appears in {patientName}'s plan for {activeDate}</p>
                </div>
              </label>
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.saveToLibrary}
                  onChange={e => setForm(p => ({ ...p, saveToLibrary: e.target.checked }))}
                  className="mt-0.5 accent-[#1E7C45]"
                />
                <div>
                  <p className="text-sm font-medium text-[#374151]">Also save to my recipe library</p>
                  <p className="text-xs text-[#9CA3AF]">Makes this recipe searchable for future patients</p>
                </div>
              </label>
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
              >
                {addSuccess ? '✓ Added' : 'Add Meal'}
              </button>
              <button
                type="button"
                onClick={() => { setShowAddForm(false); setForm(EMPTY_FORM); }}
                className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB] transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
