import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { doctorApi, MealEntry, FoodItemSummary } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import {
  MoreHorizontal, StickyNote, Flame, Beef, Wheat, Droplets,
  Plus, X, Loader2, AlertCircle, CalendarDays, Pencil, Save, Check,
} from 'lucide-react';

interface PlanTabProps {
  patientId: number;
  patientTdee: number;
  patientName: string;
  patientDietType: string;
}

interface CustomMealForm {
  name: string;
  mealType: string;
  calories: string;
  protein: string;
  carbs: string;
  fat: string;
  fiber: string;
  diet_type: string;
  submitToGlobal: boolean;
}

const MEAL_TYPES = ['Breakfast', 'MorningSnacks', 'Lunch', 'EveningSnacks', 'Dinner'];

// Infer slot_type from meal type for the recipe submission
function inferSlotType(mealType: string): string {
  if (mealType === 'Breakfast') return 'main_dish';
  if (mealType === 'MorningSnacks' || mealType === 'EveningSnacks') return 'snack_item';
  return 'main_dish'; // Lunch / Dinner — covers most cases
}

// Infer meal_time_tags from meal type
function inferMealTimeTags(mealType: string): string[] {
  if (mealType === 'Breakfast') return ['Breakfast'];
  if (mealType === 'MorningSnacks') return ['Morning_Snack'];
  if (mealType === 'EveningSnacks') return ['Evening_Snack'];
  if (mealType === 'Lunch') return ['Lunch'];
  if (mealType === 'Dinner') return ['Dinner'];
  return ['Lunch', 'Dinner'];
}

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
    return new Date(dateStr).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return dateStr; }
}

function MacroPill({ icon, value, unit, color }: { icon: React.ReactNode; value: number; unit: string; color: string }) {
  return (
    <span className={`flex items-center gap-1 text-xs ${color}`}>
      {icon}
      <span className="tabular-nums font-medium">{Math.round(value)}</span>
      <span className="text-[#9CA3AF]">{unit}</span>
    </span>
  );
}

// ── MealCard with working per-meal notes ──────────────────────────────────────
function MealCard({
  meal, patientId, onNoteAdded,
}: {
  meal: MealEntry;
  patientId: number;
  onNoteAdded: () => void;
}) {
  const [menuOpen, setMenuOpen]       = useState(false);
  const [noteOpen, setNoteOpen]       = useState(false);
  const [noteText, setNoteText]       = useState(meal.doctor_note ?? '');
  const [saving, setSaving]           = useState(false);

  const handleSaveNote = async () => {
    if (!noteText.trim()) return;
    setSaving(true);
    try {
      await doctorApi.addMealNote(patientId, meal.Date, meal['Meal Type'], noteText.trim());
      toast.success('Note saved to meal');
      setNoteOpen(false);
      onNoteAdded();
    } catch {
      toast.error('Failed to save note');
    } finally {
      setSaving(false);
    }
  };

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
              <div className="absolute right-0 top-8 z-20 w-36 bg-white rounded-lg border border-[#E5E7EB] shadow-lg py-1">
                <button
                  onClick={() => { setMenuOpen(false); setNoteText(meal.doctor_note ?? ''); setNoteOpen(true); }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-[#374151] hover:bg-[#F9FAFB]"
                >
                  <StickyNote size={13} className="text-[#6B7280]" />
                  {meal.doctor_note ? 'Edit note' : 'Add note'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <p className="text-sm font-medium text-[#111827] mb-3 leading-snug">{meal['Menu Names']}</p>

      <div className="flex items-center gap-3 flex-wrap">
        <MacroPill icon={<Flame size={11} />}    value={meal['Total Calories']} unit="kcal" color="text-[#DC2626]" />
        <MacroPill icon={<Beef size={11} />}     value={meal['Total Protein']}  unit="g P"  color="text-[#2563EB]" />
        <MacroPill icon={<Wheat size={11} />}    value={meal['Total Carbs']}    unit="g C"  color="text-[#F59E0B]" />
        <MacroPill icon={<Droplets size={11} />} value={meal['Total Fat']}      unit="g F"  color="text-[#6B7280]" />
      </div>

      {/* Existing note display */}
      {meal.doctor_note && !noteOpen && (
        <div className="mt-3 px-3 py-2 bg-[#F0FDF4] rounded-md border border-[#DCFCE7]">
          <p className="text-xs text-[#15803d] flex items-start gap-1.5">
            <StickyNote size={11} className="mt-0.5 flex-shrink-0" />
            <span>{meal.doctor_note}</span>
          </p>
        </div>
      )}

      {/* Inline note editor */}
      {noteOpen && (
        <div className="mt-3">
          <textarea
            value={noteText}
            onChange={e => setNoteText(e.target.value)}
            rows={2}
            autoFocus
            placeholder="Add a note for this meal…"
            className="w-full resize-none text-sm px-2 py-1.5 border border-[#DCFCE7] rounded bg-[#F0FDF4] text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
          />
          <div className="flex gap-2 mt-1.5">
            <button onClick={handleSaveNote} disabled={saving || !noteText.trim()}
              className="flex items-center gap-1.5 h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
              {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
              Save
            </button>
            <button onClick={() => setNoteOpen(false)}
              className="h-7 px-3 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151] hover:bg-[#F9FAFB]">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function PlanTab({ patientId, patientTdee, patientName, patientDietType }: PlanTabProps) {
  const queryClient = useQueryClient();
  const [activeDateIdx, setActiveDateIdx] = useState(0);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const EMPTY_FORM: CustomMealForm = {
    name: '', mealType: 'Breakfast', calories: '', protein: '',
    carbs: '', fat: '', fiber: '', diet_type: patientDietType,
    submitToGlobal: false,
  };
  const [form, setForm] = useState<CustomMealForm>(EMPTY_FORM);

  const overrideMutation = useMutation({
    mutationFn: (notes: string) => doctorApi.overridePlan(patientId, { doctor_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) });
      setEditingNotes(false);
      toast.success('Plan notes saved');
    },
    onError: () => toast.error('Failed to save notes'),
  });

  const { data: plan, isLoading, isError } = useQuery({
    queryKey: qk.patientPlan(patientId),
    queryFn: () => doctorApi.getPatientPlan(patientId),
  });

  if (isLoading) return <div className="flex items-center justify-center py-20"><Loader2 size={24} className="animate-spin text-[#1E7C45]" /></div>;

  if (isError || !plan) {
    return (
      <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
        <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
        <p className="text-base font-medium text-[#374151]">No active plan</p>
        <p className="text-sm text-[#6B7280] mt-1">{patientName} doesn't have an active meal plan yet.</p>
      </div>
    );
  }

  const grouped = groupByDate(plan.meals);
  const dates = Object.keys(grouped).sort();
  if (dates.length === 0) return (
    <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
      <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
      <p className="text-base font-medium text-[#374151]">Plan has no meals yet</p>
    </div>
  );

  const activeDate = dates[activeDateIdx] ?? dates[0];
  const dayMeals = grouped[activeDate] ?? [];
  const totalCalories = dayMeals.reduce((s, m) => s + (m['Total Calories'] ?? 0), 0);
  const totalProtein  = dayMeals.reduce((s, m) => s + (m['Total Protein']  ?? 0), 0);
  const totalCarbs    = dayMeals.reduce((s, m) => s + (m['Total Carbs']    ?? 0), 0);
  const totalFat      = dayMeals.reduce((s, m) => s + (m['Total Fat']      ?? 0), 0);

  // ── Add Custom Meal handler (2-step: create recipe → assign to patient) ──
  const handleAddMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.calories) { toast.error('Recipe name and calories are required'); return; }
    setSubmitting(true);
    try {
      // Step 1: Save to doctor's library (and optionally flag for global)
      const newRecipe = await doctorApi.addRecipe({
        recipe_name:         form.name.trim(),
        slot_type:           inferSlotType(form.mealType),
        cal_per_serving:     parseFloat(form.calories),
        protein_per_serving: parseFloat(form.protein) || 0,
        carbs_per_serving:   parseFloat(form.carbs)   || 0,
        fat_per_serving:     parseFloat(form.fat)     || 0,
        fiber_per_serving:   parseFloat(form.fiber)   || 0,
        diet_type:           form.diet_type,
        meal_time_tags:      inferMealTimeTags(form.mealType),
        plan_type_tags:      ['Healthy', 'Diabetic-Friendly', 'Gym-Friendly'],
        ingredients:         [],
        region_tags:         [],
        submit_to_global:    form.submitToGlobal,
      });

      // Step 2: Assign this recipe to the patient's plan on the active date
      await doctorApi.assignRecipe(newRecipe.id, {
        patient_ids: [patientId],
        meal_type:   form.mealType,
        meal_date:   activeDate,
      });

      queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) });
      const globalMsg = form.submitToGlobal ? ' (submitted for admin review to add to global dataset)' : '';
      toast.success(`"${form.name}" added to ${patientName}'s plan${globalMsg}`);
      setShowAddForm(false);
      setForm(EMPTY_FORM);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to add meal');
    } finally {
      setSubmitting(false);
    }
  };

  const f = (key: keyof CustomMealForm, label: string, type = 'text', placeholder = '') => (
    <div key={String(key)}>
      <label className="block text-xs font-medium text-[#374151] mb-1">{label}</label>
      <input required={type === 'number'} type={type} min={type === 'number' ? 0 : undefined}
        value={form[key] as string}
        onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
      />
    </div>
  );

  return (
    <div className="max-w-4xl">
      {/* Plan-level doctor notes banner */}
      {plan.doctor_notes && !editingNotes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-[#15803d]">Doctor Notes</p>
            <button onClick={() => { setNotesValue(plan.doctor_notes ?? ''); setEditingNotes(true); }}
              className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline">
              <Pencil size={11} /> Edit
            </button>
          </div>
          <p className="text-sm text-[#374151]">{plan.doctor_notes}</p>
        </div>
      )}
      {editingNotes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <p className="text-xs font-medium text-[#15803d] mb-1">Doctor Notes</p>
          <textarea value={notesValue} onChange={e => setNotesValue(e.target.value)} rows={3} autoFocus
            className="w-full resize-none bg-white border border-[#DCFCE7] rounded px-2 py-1.5 text-sm text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            placeholder="Notes visible to the patient on their plan…" />
          <div className="flex gap-2 mt-2">
            <button onClick={() => overrideMutation.mutate(notesValue)} disabled={overrideMutation.isPending}
              className="flex items-center gap-1.5 h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
              {overrideMutation.isPending ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />} Save
            </button>
            <button onClick={() => setEditingNotes(false)} className="h-7 px-3 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151]">Cancel</button>
          </div>
        </div>
      )}
      {!plan.doctor_notes && !editingNotes && (
        <button onClick={() => { setNotesValue(''); setEditingNotes(true); }}
          className="flex items-center gap-2 h-8 px-3 mb-4 rounded-md border border-dashed border-[#D1D5DB] text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45]">
          <Pencil size={12} /> Add doctor notes to this plan
        </button>
      )}

      {/* Day selector */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        {dates.map((date, idx) => (
          <button key={date} onClick={() => setActiveDateIdx(idx)}
            className={`h-8 px-3 text-sm font-medium rounded-md transition-colors ${
              activeDateIdx === idx ? 'bg-[#1E7C45] text-white' : 'bg-white border border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:text-[#374151]'
            }`}>
            {formatDate(date)}
          </button>
        ))}
      </div>

      {/* Day heading + totals */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#111827]">{activeDate} — Meal Plan</h2>
          <p className="text-sm text-[#6B7280]">{dayMeals.length} meals planned</p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-[#6B7280]">Day total:</span>
          <span className="font-semibold text-[#111827] tabular-nums">{Math.round(totalCalories)} kcal</span>
          <span className="text-xs text-[#9CA3AF]">P:{Math.round(totalProtein)}g · C:{Math.round(totalCarbs)}g · F:{Math.round(totalFat)}g</span>
        </div>
      </div>

      {/* TDEE bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-[#374151]">Calories vs TDEE</span>
          <span className="text-sm text-[#6B7280] tabular-nums">{Math.round(totalCalories)} / {Math.round(patientTdee)} kcal</span>
        </div>
        <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
          <div className="h-full bg-[#1E7C45] rounded-full" style={{ width: `${Math.min(100, (totalCalories / patientTdee) * 100)}%` }} />
        </div>
        <p className="text-xs text-[#6B7280] mt-1.5">
          {totalCalories < patientTdee
            ? `${Math.round(patientTdee - totalCalories)} kcal below TDEE`
            : `${Math.round(totalCalories - patientTdee)} kcal above TDEE`}
        </p>
      </div>

      {/* Meal cards with working per-meal notes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {dayMeals.map((meal, i) => (
          <MealCard key={i} meal={meal} patientId={patientId}
            onNoteAdded={() => queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) })} />
        ))}
      </div>

      {/* Add Custom Meal button / form */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 h-9 px-4 rounded-md border border-dashed border-[#D1D5DB] text-sm text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] transition-colors w-full justify-center"
        >
          <Plus size={14} /> Add Custom Meal to {activeDate}
        </button>
      ) : (
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#111827]">Add Custom Meal — {activeDate}</h3>
            <button onClick={() => { setShowAddForm(false); setForm(EMPTY_FORM); }}
              className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
              <X size={15} />
            </button>
          </div>

          <form onSubmit={handleAddMeal}>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {/* Recipe name — full width */}
              <div className="col-span-2">
                <label className="block text-xs font-medium text-[#374151] mb-1">
                  Recipe Name <span className="text-[#DC2626]">*</span>
                </label>
                <input required type="text" value={form.name}
                  onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. Masoor Dal Soup"
                  className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                />
              </div>

              {/* Meal type */}
              <div>
                <label className="block text-xs font-medium text-[#374151] mb-1">Meal Type</label>
                <select value={form.mealType} onChange={e => setForm(p => ({ ...p, mealType: e.target.value }))}
                  className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
                  {MEAL_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>

              {/* Diet type */}
              <div>
                <label className="block text-xs font-medium text-[#374151] mb-1">Diet Type</label>
                <select value={form.diet_type} onChange={e => setForm(p => ({ ...p, diet_type: e.target.value }))}
                  className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
                  {['Vegetarian', 'Non-Vegetarian', 'Eggetarian'].map(t => <option key={t}>{t}</option>)}
                </select>
              </div>

              {f('calories', 'Calories (kcal) *', 'number', '0')}
              {f('protein',  'Protein (g)',       'number', '0')}
              {f('carbs',    'Carbs (g)',         'number', '0')}
              {f('fat',      'Fat (g)',           'number', '0')}
              {f('fiber',    'Fiber (g)',         'number', '0')}
            </div>

            {/* Library / Global dataset options */}
            <div className="border border-[#E5E7EB] rounded-md p-3 mb-4 bg-[#F9FAFB] space-y-3">
              {/* Always saved to library — fixed, non-interactive */}
              <label className="flex items-start gap-2.5 cursor-default">
                <div className="mt-0.5 w-4 h-4 rounded border-2 border-[#1E7C45] bg-[#1E7C45] flex items-center justify-center flex-shrink-0">
                  <Check size={10} className="text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#374151]">Save to my recipe library</p>
                  <p className="text-xs text-[#9CA3AF]">
                    Always saved — you can reuse this meal for any of your patients without re-entering it.
                  </p>
                </div>
              </label>

              {/* Optional: also submit for global dataset */}
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input type="checkbox" checked={form.submitToGlobal}
                  onChange={e => setForm(p => ({ ...p, submitToGlobal: e.target.checked }))}
                  className="mt-0.5 accent-[#1E7C45] w-4 h-4 flex-shrink-0"
                />
                <div>
                  <p className="text-sm font-medium text-[#374151]">Also submit to global dataset</p>
                  <p className="text-xs text-[#9CA3AF]">
                    Sends to admin for review. Once approved, this meal joins the shared dataset
                    used by all doctors and the AI meal generator.
                  </p>
                </div>
              </label>
            </div>

            <div className="flex gap-3">
              <button type="submit" disabled={submitting}
                className="flex items-center gap-2 h-9 px-5 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50">
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                Add Meal
              </button>
              <button type="button" onClick={() => { setShowAddForm(false); setForm(EMPTY_FORM); }}
                className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB]">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
