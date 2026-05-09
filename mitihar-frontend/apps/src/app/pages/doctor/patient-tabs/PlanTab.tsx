import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { doctorApi, MealEntry, FoodItemSummary } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import {
  MoreHorizontal, StickyNote, Flame, Beef, Wheat, Droplets,
  Plus, X, Loader2, AlertCircle, CalendarDays, Pencil, Save,
  Search, Sparkles,
} from 'lucide-react';

interface PlanTabProps {
  patientId: number;
  patientTdee: number;
  patientName: string;
  patientDietType: string;
  patientMealsPerDay: number;   // Task 1 — new prop
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
}

// Task 1 — meal slots filtered by patient preference
const ALL_MEAL_TYPES  = ['Breakfast', 'MorningSnacks', 'Lunch', 'EveningSnacks', 'Dinner'];
const THREE_MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner'];

function getMealTypes(mealsPerDay: number): string[] {
  return mealsPerDay >= 5 ? ALL_MEAL_TYPES : THREE_MEAL_TYPES;
}

function inferSlotType(mealType: string): string {
  if (mealType === 'MorningSnacks' || mealType === 'EveningSnacks') return 'snack_item';
  return 'main_dish';
}

function inferMealTimeTags(mealType: string): string[] {
  if (mealType === 'Breakfast')     return ['Breakfast'];
  if (mealType === 'MorningSnacks') return ['Morning_Snack'];
  if (mealType === 'EveningSnacks') return ['Evening_Snack'];
  if (mealType === 'Lunch')         return ['Lunch'];
  if (mealType === 'Dinner')        return ['Dinner'];
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
    return new Date(dateStr).toLocaleDateString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short',
    });
  } catch { return dateStr; }
}

function MacroPill({ icon, value, unit, color }: {
  icon: React.ReactNode; value: number; unit: string; color: string;
}) {
  return (
    <span className={`flex items-center gap-1 text-xs ${color}`}>
      {icon}
      <span className="tabular-nums font-medium">{Math.round(value)}</span>
      <span className="text-[#9CA3AF]">{unit}</span>
    </span>
  );
}

// ── Task 3: MealCard with inline edit + note ──────────────────────────────
function MealCard({
  meal, patientId, allMeals, onUpdated,
}: {
  meal: MealEntry;
  patientId: number;
  allMeals: MealEntry[];
  onUpdated: () => void;
}) {
  const [menuOpen, setMenuOpen]   = useState(false);
  const [noteOpen, setNoteOpen]   = useState(false);
  const [editOpen, setEditOpen]   = useState(false);
  const [noteText, setNoteText]   = useState(meal.doctor_note ?? '');
  const [saving,   setSaving]     = useState(false);

  // Edit form state — pre-filled from current meal
  const [editForm, setEditForm] = useState({
    name:     meal['Menu Names'],
    calories: String(Math.round(meal['Total Calories'])),
    protein:  String(Math.round(meal['Total Protein'])),
    carbs:    String(Math.round(meal['Total Carbs'])),
    fat:      String(Math.round(meal['Total Fat'])),
    fiber:    String(Math.round(meal['Total Fiber'] ?? 0)),
  });

  const handleSaveNote = async () => {
    if (!noteText.trim()) return;
    setSaving(true);
    try {
      await doctorApi.addMealNote(patientId, meal.Date, meal['Meal Type'], noteText.trim());
      toast.success('Note saved');
      setNoteOpen(false);
      onUpdated();
    } catch { toast.error('Failed to save note'); }
    finally   { setSaving(false); }
  };

  const handleSaveEdit = async () => {
    if (!editForm.name.trim() || !editForm.calories) {
      toast.error('Name and calories are required');
      return;
    }
    setSaving(true);
    try {
      // Build updated meals array — swap only this meal
      const updatedMeals = allMeals.map(m => {
        if (m.Date === meal.Date && m['Meal Type'] === meal['Meal Type']) {
          return {
            ...m,
            'Menu Names':     editForm.name.trim(),
            'Total Calories': parseFloat(editForm.calories) || 0,
            'Total Protein':  parseFloat(editForm.protein)  || 0,
            'Total Carbs':    parseFloat(editForm.carbs)    || 0,
            'Total Fat':      parseFloat(editForm.fat)      || 0,
            'Total Fiber':    parseFloat(editForm.fiber)    || 0,
          };
        }
        return m;
      });
      await doctorApi.overridePlan(patientId, { meals: updatedMeals });
      toast.success('Meal updated');
      setEditOpen(false);
      onUpdated();
    } catch { toast.error('Failed to update meal'); }
    finally   { setSaving(false); }
  };

  const ef = (key: keyof typeof editForm, label: string) => (
    <div key={key}>
      <label className="block text-xs font-medium text-[#374151] mb-1">{label}</label>
      <input
        type={key === 'name' ? 'text' : 'number'} min={0}
        value={editForm[key]}
        onChange={e => setEditForm(p => ({ ...p, [key]: e.target.value }))}
        className="w-full h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
      />
    </div>
  );

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 group relative
                    hover:border-[#D1D5DB] transition-colors">
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
            className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF]
                       opacity-0 group-hover:opacity-100 hover:bg-[#F3F4F6]
                       hover:text-[#374151] transition-all"
          >
            <MoreHorizontal size={15} />
          </button>
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} onKeyDown={(e) => e.key === "Escape" && setMenuOpen(false)} role="button" aria-label="Close menu" tabIndex={-1} />
              <div className="absolute right-0 top-8 z-20 w-36 bg-white rounded-lg
                              border border-[#E5E7EB] shadow-lg py-1">
                <button
                  onClick={() => {
                    setMenuOpen(false);
                    setEditForm({
                      name:     meal['Menu Names'],
                      calories: String(Math.round(meal['Total Calories'])),
                      protein:  String(Math.round(meal['Total Protein'])),
                      carbs:    String(Math.round(meal['Total Carbs'])),
                      fat:      String(Math.round(meal['Total Fat'])),
                      fiber:    String(Math.round(meal['Total Fiber'] ?? 0)),
                    });
                    setEditOpen(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm
                             text-[#374151] hover:bg-[#F9FAFB]"
                >
                  <Pencil size={13} className="text-[#6B7280]" />
                  Edit meal
                </button>
                <button
                  onClick={() => {
                    setMenuOpen(false);
                    setNoteText(meal.doctor_note ?? '');
                    setNoteOpen(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm
                             text-[#374151] hover:bg-[#F9FAFB]"
                >
                  <StickyNote size={13} className="text-[#6B7280]" />
                  {meal.doctor_note ? 'Edit note' : 'Add note'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Meal name */}
      <p className="text-sm font-medium text-[#111827] mb-3 leading-snug">
        {meal['Menu Names']}
      </p>

      <div className="flex items-center gap-3 flex-wrap">
        <MacroPill icon={<Flame size={11} />}    value={meal['Total Calories']} unit="kcal" color="text-[#DC2626]" />
        <MacroPill icon={<Beef size={11} />}     value={meal['Total Protein']}  unit="g P"  color="text-[#2563EB]" />
        <MacroPill icon={<Wheat size={11} />}    value={meal['Total Carbs']}    unit="g C"  color="text-[#F59E0B]" />
        <MacroPill icon={<Droplets size={11} />} value={meal['Total Fat']}      unit="g F"  color="text-[#6B7280]" />
      </div>

      {/* Existing note display */}
      {meal.doctor_note && !noteOpen && !editOpen && (
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
            placeholder="Add a note for this meal…"
            className="w-full resize-none text-sm px-2 py-1.5 border border-[#DCFCE7]
                       rounded bg-[#F0FDF4] text-[#374151] focus:outline-none
                       focus:ring-2 focus:ring-[#1E7C45]"
          />
          <div className="flex gap-2 mt-1.5">
            <button onClick={handleSaveNote} disabled={saving || !noteText.trim()}
              className="flex items-center gap-1.5 h-7 px-3 rounded bg-[#1E7C45]
                         text-white text-xs hover:bg-[#166534] disabled:opacity-50">
              {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
              Save
            </button>
            <button onClick={() => setNoteOpen(false)}
              className="h-7 px-3 rounded border border-[#D1D5DB] bg-white text-xs
                         text-[#374151] hover:bg-[#F9FAFB]">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Task 3 — Inline meal editor */}
      {editOpen && (
        <div className="mt-3 border border-[#E5E7EB] rounded-lg p-3 bg-[#F9FAFB]">
          <p className="text-xs font-semibold text-[#374151] mb-2">Edit Meal</p>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div className="col-span-2">{ef('name',     'Dish Name')}</div>
            {ef('calories', 'Calories')}
            {ef('protein',  'Protein (g)')}
            {ef('carbs',    'Carbs (g)')}
            {ef('fat',      'Fat (g)')}
            <div className="col-span-2">{ef('fiber', 'Fiber (g)')}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleSaveEdit} disabled={saving}
              className="flex items-center gap-1.5 h-7 px-3 rounded bg-[#1E7C45]
                         text-white text-xs hover:bg-[#166534] disabled:opacity-50">
              {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
              Save Changes
            </button>
            <button onClick={() => setEditOpen(false)}
              className="h-7 px-3 rounded border border-[#D1D5DB] bg-white text-xs
                         text-[#374151] hover:bg-[#F9FAFB]">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Task 4: Autocomplete search hook ─────────────────────────────────────
// results and loading are merged into one state object so they update
// atomically — eliminates the intermediate render where loading=true
// but results still show stale data from the previous query.
function useRecipeSearch(query: string) {
  const [state, setState] = useState<{ results: FoodItemSummary[]; loading: boolean }>(
    { results: [], loading: false },
  );
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (query.length < 2) {
      setState({ results: [], loading: false });
      return;
    }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setState({ results: [], loading: true });       // clear stale + show spinner in one render
      try {
        const data = await doctorApi.browseRecipes({ search: query });
        setState({ results: data, loading: false });  // data + hide spinner in one render
      } catch {
        setState({ results: [], loading: false });
      }
    }, 300);
    return () => clearTimeout(timerRef.current);
  }, [query]);

  return { results: state.results, loading: state.loading };
}

// ── Task 4: Gemini nutrition lookup ──────────────────────────────────────
async function fetchNutritionFromGemini(
  foodName: string,
): Promise<Partial<CustomMealForm>> {
  const { data } = await (await import('../../../../lib/axios')).default.post(
    '/doctor/recipes/lookup',
    { food_name: foodName },
  );
  return data;
}

// ── Main PlanTab component ────────────────────────────────────────────────

// ── DaySelector ────────────────────────────────────────────────────────────────
interface DaySelectorProps {
  dates: string[];
  activeDateIdx: number;
  onSelect: (idx: number) => void;
}

function DaySelector({ dates, activeDateIdx, onSelect }: DaySelectorProps) {
  return (
    <div className="flex items-center gap-2 mb-5 flex-wrap">
      {dates.map((date, idx) => (
        <button key={date} onClick={() => onSelect(idx)}
          className={`h-8 px-3 text-sm font-medium rounded-md transition-colors ${
            activeDateIdx === idx
              ? 'bg-[#1E7C45] text-white'
              : 'bg-white border border-[#E5E7EB] text-[#6B7280] hover:border-[#D1D5DB] hover:text-[#374151]'
          }`}>
          {formatDate(date)}
        </button>
      ))}
    </div>
  );
}

// ── TdeeProgressBar ────────────────────────────────────────────────────────────
interface TdeeProgressBarProps {
  totalCalories: number;
  patientTdee: number;
  patientMealsPerDay: number;
}

function TdeeProgressBar({ totalCalories, patientTdee, patientMealsPerDay }: TdeeProgressBarProps) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 mb-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[#374151]">
          Calories vs TDEE
          <span className="text-xs text-[#9CA3AF] ml-1.5">({patientMealsPerDay}-meal plan)</span>
        </span>
        <span className="text-sm text-[#6B7280] tabular-nums">
          {Math.round(totalCalories)} / {Math.round(patientTdee)} kcal
        </span>
      </div>
      <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
        <div className="h-full bg-[#1E7C45] rounded-full"
          style={{ width: `${Math.min(100, (totalCalories / patientTdee) * 100)}%` }} />
      </div>
      <p className="text-xs text-[#6B7280] mt-1.5">
        {totalCalories < patientTdee
          ? `${Math.round(patientTdee - totalCalories)} kcal below TDEE`
          : `${Math.round(totalCalories - patientTdee)} kcal above TDEE`}
      </p>
    </div>
  );
}

// ── AddMealForm ───────────────────────────────────────────────────────────────
// Extracted from PlanTab to keep the main component focused on plan display.
// Owns all "add custom meal" state. When showAddForm becomes false, this
// component unmounts and all state resets automatically on next open.
interface AddMealFormProps {
  patientId: number;
  activeDate: string;
  patientDietType: string;
  patientName: string;
  mealTypes: string[];
  onClose: () => void;
}

function AddMealForm({
  patientId, activeDate, patientDietType, patientName, mealTypes, onClose,
}: AddMealFormProps) {
  const queryClient = useQueryClient();

  const EMPTY_FORM: CustomMealForm = {
    name: '', mealType: 'Breakfast', calories: '', protein: '',
    carbs: '', fat: '', fiber: '', diet_type: patientDietType,
  };

  const [form,          setForm]         = useState<CustomMealForm>(EMPTY_FORM);
  const [submitting,    setSubmitting]   = useState(false);
  const [geminiLoading, setGeminiLoading]= useState(false);
  const [showDropdown,  setShowDropdown] = useState(false);

  const { results: searchResults, loading: searchLoading } = useRecipeSearch(form.name);

  const handleSelectRecipe = (recipe: FoodItemSummary) => {
    setForm(p => ({
      ...p,
      name:      recipe.recipe_name,
      calories:  String(recipe.cal_per_serving),
      protein:   String(recipe.protein_per_serving),
      carbs:     String(recipe.carbs_per_serving),
      fat:       String(recipe.fat_per_serving),
      fiber:     String(recipe.fiber_per_serving),
      diet_type: recipe.diet_type,
    }));
    setShowDropdown(false);
  };

  const handleGeminiLookup = async () => {
    if (!form.name.trim()) { toast.error('Enter a dish name first'); return; }
    setGeminiLoading(true);
    try {
      const data = await fetchNutritionFromGemini(form.name.trim());
      setForm(p => ({
        ...p,
        calories: data.calories ?? p.calories,
        protein:  data.protein  ?? p.protein,
        carbs:    data.carbs    ?? p.carbs,
        fat:      data.fat      ?? p.fat,
        fiber:    data.fiber    ?? p.fiber,
      }));
      toast.success('Nutrition data filled from AI — please verify');
    } catch { toast.error('AI lookup failed — enter values manually'); }
    finally   { setGeminiLoading(false); }
  };

  const handleAddMeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.calories) {
      toast.error('Recipe name and calories are required');
      return;
    }
    setSubmitting(true);
    try {
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
        submit_to_global:    true,
      });
      await doctorApi.assignRecipe(newRecipe.id, {
        patient_ids: [patientId],
        meal_type:   form.mealType,
        meal_date:   activeDate,
      });
      queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) });
      toast.success(`"${form.name}" added to ${patientName}'s plan and saved to dataset`);
      onClose();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to add meal');
    } finally {
      setSubmitting(false);
    }
  };

  const numField = (key: keyof CustomMealForm, label: string) => (
    <div key={String(key)}>
      <label className="block text-xs font-medium text-[#374151] mb-1">{label}</label>
      <input type="number" min={0}
        value={form[key] as string}
        onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
        className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm
                   focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
      />
    </div>
  );

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#111827]">Add Custom Meal — {activeDate}</h3>
        <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
          <X size={15} />
        </button>
      </div>

      <form onSubmit={handleAddMeal}>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {/* Dish name with autocomplete + AI lookup */}
          <div className="col-span-2 relative">
            <label htmlFor="plan-dish-name" className="block text-xs font-medium text-[#374151] mb-1">
              Dish Name <span className="text-[#DC2626]">*</span>
            </label>
            <div className="relative flex gap-2">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
                <input
                  id="plan-dish-name" required type="text" value={form.name}
                  onChange={e => { setForm(p => ({ ...p, name: e.target.value })); setShowDropdown(true); }}
                  onFocus={() => setShowDropdown(true)}
                  placeholder="e.g. Masoor Dal Soup"
                  className="w-full h-9 pl-8 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                />
                {showDropdown && form.name.length >= 2 && (
                  <div className="absolute top-full left-0 right-0 z-30 mt-1 bg-white border border-[#E5E7EB] rounded-lg shadow-lg max-h-48 overflow-y-auto">
                    {searchLoading && (
                      <div className="flex items-center gap-2 px-3 py-2 text-sm text-[#6B7280]">
                        <Loader2 size={12} className="animate-spin" /> Searching…
                      </div>
                    )}
                    {!searchLoading && searchResults.length === 0 && (
                      <div className="px-3 py-2 text-sm text-[#9CA3AF]">No matches — use AI lookup below</div>
                    )}
                    {searchResults.map(r => (
                      <button key={r.id} type="button" onClick={() => handleSelectRecipe(r)}
                        className="w-full text-left px-3 py-2 hover:bg-[#F9FAFB] border-b border-[#F3F4F6] last:border-0">
                        <p className="text-sm font-medium text-[#111827]">{r.recipe_name}</p>
                        <p className="text-xs text-[#9CA3AF]">{Math.round(r.cal_per_serving)} kcal · {r.diet_type}</p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button type="button" onClick={handleGeminiLookup}
                disabled={geminiLoading || !form.name.trim()} title="Fetch nutrition from AI"
                className="flex items-center gap-1.5 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] disabled:opacity-40 whitespace-nowrap">
                {geminiLoading ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                AI Lookup
              </button>
            </div>
          </div>

          {/* Meal type */}
          <div>
            <label htmlFor="plan-meal-type" className="block text-xs font-medium text-[#374151] mb-1">Meal Type</label>
            <select id="plan-meal-type" value={form.mealType}
              onChange={e => setForm(p => ({ ...p, mealType: e.target.value }))}
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
              {mealTypes.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>

          {/* Diet type */}
          <div>
            <label htmlFor="plan-diet-type" className="block text-xs font-medium text-[#374151] mb-1">Diet Type</label>
            <select id="plan-diet-type" value={form.diet_type}
              onChange={e => setForm(p => ({ ...p, diet_type: e.target.value }))}
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
              {['Vegetarian', 'Non-Vegetarian', 'Eggetarian'].map(t => <option key={t}>{t}</option>)}
            </select>
          </div>

          {numField('calories', 'Calories (kcal) *')}
          {numField('protein',  'Protein (g)')}
          {numField('carbs',    'Carbs (g)')}
          {numField('fat',      'Fat (g)')}
          {numField('fiber',    'Fiber (g)')}
        </div>

        <div className="border border-[#E5E7EB] rounded-md px-3 py-2 mb-4 bg-[#F9FAFB] text-xs text-[#6B7280]">
          ✅ This meal will be saved to your library and submitted to the global dataset for admin review.
        </div>

        <div className="flex gap-3">
          <button type="submit" disabled={submitting}
            className="flex items-center gap-2 h-9 px-5 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166634] disabled:opacity-50">
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Add Meal
          </button>
          <button type="button" onClick={onClose}
            className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB]">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export function PlanTab({
  patientId, patientTdee, patientName, patientDietType, patientMealsPerDay,
}: PlanTabProps) {
  const queryClient  = useQueryClient();
  const [activeDateIdx,  setActiveDateIdx]  = useState(0);
  const [showAddForm,    setShowAddForm]     = useState(false);
  const [editingNotes,   setEditingNotes]    = useState(false);
  const [notesValue,     setNotesValue]      = useState('');
  const mealTypes = getMealTypes(patientMealsPerDay); // Task 1

  const overrideMutation = useMutation({
    mutationFn: (notes: string) =>
      doctorApi.overridePlan(patientId, { doctor_notes: notes }),
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

  if (isLoading) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
    </div>
  );

  if (isError || !plan) return (
    <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
      <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
      <p className="text-base font-medium text-[#374151]">No active plan</p>
      <p className="text-sm text-[#6B7280] mt-1">
        {patientName} doesn't have an active meal plan yet.
      </p>
    </div>
  );

  const grouped    = groupByDate(plan.meals);
  const dates      = Object.keys(grouped).sort();

  if (dates.length === 0) return (
    <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
      <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
      <p className="text-base font-medium text-[#374151]">Plan has no meals yet</p>
    </div>
  );

  const activeDate = dates[activeDateIdx] ?? dates[0];
  // Task 1 — filter to patient's meal count
  const allDayMeals = grouped[activeDate] ?? [];
  const dayMeals    = allDayMeals.filter(m =>
    mealTypes.includes(m['Meal Type'])
  );

  const totalCalories = dayMeals.reduce((s, m) => s + (m['Total Calories'] ?? 0), 0);
  const totalProtein  = dayMeals.reduce((s, m) => s + (m['Total Protein']  ?? 0), 0);
  const totalCarbs    = dayMeals.reduce((s, m) => s + (m['Total Carbs']    ?? 0), 0);
  const totalFat      = dayMeals.reduce((s, m) => s + (m['Total Fat']      ?? 0), 0);

  return (
    <div className="max-w-4xl">
      {/* Plan-level doctor notes */}
      {plan.doctor_notes && !editingNotes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-[#15803d]">Doctor Notes</p>
            <button
              onClick={() => { setNotesValue(plan.doctor_notes ?? ''); setEditingNotes(true); }}
              className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline"
            >
              <Pencil size={11} /> Edit
            </button>
          </div>
          <p className="text-sm text-[#374151]">{plan.doctor_notes}</p>
        </div>
      )}
      {editingNotes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <p className="text-xs font-medium text-[#15803d] mb-1">Doctor Notes</p>
          <textarea value={notesValue} onChange={e => setNotesValue(e.target.value)}
            rows={3}
            className="w-full resize-none bg-white border border-[#DCFCE7] rounded
                       px-2 py-1.5 text-sm text-[#374151] focus:outline-none
                       focus:ring-2 focus:ring-[#1E7C45]"
            placeholder="Notes visible to the patient on their plan…"
          />
          <div className="flex gap-2 mt-2">
            <button onClick={() => overrideMutation.mutate(notesValue)}
              disabled={overrideMutation.isPending}
              className="flex items-center gap-1.5 h-7 px-3 rounded bg-[#1E7C45]
                         text-white text-xs hover:bg-[#166534] disabled:opacity-50">
              {overrideMutation.isPending
                ? <Loader2 size={11} className="animate-spin" />
                : <Save size={11} />} Save
            </button>
            <button onClick={() => setEditingNotes(false)}
              className="h-7 px-3 rounded border border-[#D1D5DB] bg-white
                         text-xs text-[#374151]">
              Cancel
            </button>
          </div>
        </div>
      )}
      {!plan.doctor_notes && !editingNotes && (
        <button
          onClick={() => { setNotesValue(''); setEditingNotes(true); }}
          className="flex items-center gap-2 h-8 px-3 mb-4 rounded-md border
                     border-dashed border-[#D1D5DB] text-xs text-[#6B7280]
                     hover:border-[#1E7C45] hover:text-[#1E7C45]"
        >
          <Pencil size={12} /> Add doctor notes to this plan
        </button>
      )}

      <DaySelector dates={dates} activeDateIdx={activeDateIdx} onSelect={setActiveDateIdx} />

            {/* Day heading + totals */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#111827]">
            {activeDate} — Meal Plan
          </h2>
          {/* Task 1 — show meal count in context */}
          <p className="text-sm text-[#6B7280]">
            {dayMeals.length} meals · {patientMealsPerDay}-meal plan
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-[#6B7280]">Day total:</span>
          <span className="font-semibold text-[#111827] tabular-nums">
            {Math.round(totalCalories)} kcal
          </span>
          <span className="text-xs text-[#9CA3AF]">
            P:{Math.round(totalProtein)}g · C:{Math.round(totalCarbs)}g · F:{Math.round(totalFat)}g
          </span>
        </div>
      </div>

      <TdeeProgressBar totalCalories={totalCalories} patientTdee={patientTdee} patientMealsPerDay={patientMealsPerDay} />

            {/* Meal cards — Task 1 filtered, Task 3 edit enabled */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        {dayMeals.map((meal, i) => (
          <MealCard
            key={meal.id ?? `meal-${i}`}
            meal={meal}
            patientId={patientId}
            allMeals={allDayMeals}
            onUpdated={() =>
              queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) })
            }
          />
        ))}
      </div>

      {/* Add Custom Meal button / form */}
      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 h-9 px-4 rounded-md border border-dashed
                     border-[#D1D5DB] text-sm text-[#6B7280] hover:border-[#1E7C45]
                     hover:text-[#1E7C45] transition-colors w-full justify-center"
        >
          <Plus size={14} /> Add Custom Meal to {activeDate}
        </button>
      ) : (
        <AddMealForm
          patientId={patientId}
          activeDate={activeDate}
          patientDietType={patientDietType}
          patientName={patientName}
          mealTypes={mealTypes}
          onClose={() => setShowAddForm(false)}
        />
      )}
    </div>
  );
}
