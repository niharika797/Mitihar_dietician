import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { doctorApi, MealEntry, FoodItemSummary, Dish, ComboEntry } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import {
  StickyNote, Flame, Beef, Wheat, Droplets,
  Plus, X, Loader2, AlertCircle, CalendarDays, Pencil, Save,
  Search, Sparkles, ArrowLeftRight,
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
  serving_weight_g: string;
  calories: string;
  protein: string;
  carbs: string;
  fat: string;
  fiber: string;
  diet_type: string;
}

function getMealTypes(): string[] {
  return ['Breakfast', 'Lunch', 'Dinner'];
}

function inferSlotType(_mealType: string): string {
  return 'main_dish';
}

function inferMealTimeTags(mealType: string): string[] {
  if (mealType === 'Breakfast') return ['Breakfast'];
  if (mealType === 'Lunch')     return ['Lunch'];
  if (mealType === 'Dinner')    return ['Dinner'];
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

// ── DishCard ──────────────────────────────────────────────────────────────
function DishCard({ dish, index, onSwap, onRemove, removing }: {
  dish: Dish;
  index: number;
  onSwap: () => void;
  onRemove: (index: number) => void;
  removing: boolean;
}) {
  const [confirmRemove, setConfirmRemove] = useState(false);
  return (
    <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-md p-2.5">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p className="text-xs font-medium text-[#111827] leading-snug flex-1">{dish.recipe_name}</p>
        <div className="flex gap-0.5 flex-shrink-0">
          <button onClick={onSwap} title="Swap dish"
            className="w-6 h-6 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#E5E7EB] hover:text-[#1E7C45]">
            <ArrowLeftRight size={11} />
          </button>
          <button onClick={() => setConfirmRemove(true)} title="Remove dish"
            className="w-6 h-6 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#FEE2E2] hover:text-[#DC2626]">
            <X size={11} />
          </button>
        </div>
      </div>
      <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
        {dish.is_custom_override && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]">Custom</span>
        )}
        {dish.food_id && !dish.is_custom_override && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#F3F4F6] text-[#6B7280] border border-[#E5E7EB]">Library</span>
        )}
      </div>
      <div className="flex items-center gap-2.5 flex-wrap">
        <span className="flex items-center gap-0.5 text-[10px] text-[#DC2626]">
          <Flame size={9} /><span className="tabular-nums font-medium">{Math.round(dish.scaled_calories ?? dish.calories)}</span>
        </span>
        <span className="text-[10px] text-[#2563EB] tabular-nums">{dish.protein.toFixed(1)}g P</span>
        <span className="text-[10px] text-[#F59E0B] tabular-nums">{dish.carbs.toFixed(1)}g C</span>
        <span className="text-[10px] text-[#6B7280] tabular-nums">{dish.fat.toFixed(1)}g F</span>
      </div>
      {confirmRemove && (
        <div className="mt-2 p-2 bg-[#FEF2F2] border border-[#FECACA] rounded flex items-center justify-between">
          <span className="text-[10px] text-[#DC2626]">Remove this dish?</span>
          <div className="flex gap-1.5">
            <button onClick={() => { onRemove(index); setConfirmRemove(false); }} disabled={removing}
              className="h-5 px-2 rounded bg-[#DC2626] text-white text-[9px] hover:bg-[#B91C1C] disabled:opacity-50">
              {removing ? '…' : 'Remove'}
            </button>
            <button onClick={() => setConfirmRemove(false)}
              className="h-5 px-2 rounded border border-[#D1D5DB] bg-white text-[#374151] text-[9px]">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── RecipeSearchModal ─────────────────────────────────────────────────────
function RecipeSearchModal({ patientId, date, mealType, dishIndex, mode, onClose, onSuccess }: {
  patientId: number;
  date: string;
  mealType: string;
  dishIndex: number;
  mode: 'swap' | 'add';
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [query, setQuery]           = useState('');
  const [customMode, setCustomMode] = useState(false);
  const [flagForDb, setFlagForDb]   = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [customForm, setCustomForm] = useState(
    { name: '', calories: '', protein: '', carbs: '', fat: '', fiber: '' },
  );
  const { results, loading } = useRecipeSearch(query);

  const callPatch = async (body: Parameters<typeof doctorApi.patchDish>[4]) => {
    setSubmitting(true);
    try {
      await doctorApi.patchDish(patientId, date, mealType, dishIndex, body);
      toast.success(mode === 'swap' ? 'Dish swapped' : 'Dish added');
      onSuccess();
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Operation failed');
    } finally { setSubmitting(false); }
  };

  const handleCustomSubmit = () => {
    if (!customForm.name.trim() || !customForm.calories) {
      toast.error('Name and calories required');
      return;
    }
    callPatch({
      action: mode,
      custom_dish: {
        recipe_name: customForm.name.trim(),
        calories:    parseFloat(customForm.calories),
        protein:     parseFloat(customForm.protein) || 0,
        carbs:       parseFloat(customForm.carbs)   || 0,
        fat:         parseFloat(customForm.fat)     || 0,
        fiber:       parseFloat(customForm.fiber)   || 0,
      },
      flag_for_database: flagForDb,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose}
        onKeyDown={e => e.key === 'Escape' && onClose()} role="button" tabIndex={-1} aria-label="Close" />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
          <p className="text-sm font-semibold text-[#111827]">
            {mode === 'swap' ? 'Swap Dish' : 'Add Dish'} — {mealType}
          </p>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={15} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {!customMode ? (
            <>
              <div className="relative mb-3">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
                <input type="text" value={query} onChange={e => setQuery(e.target.value)}
                  placeholder="Search recipes…" autoFocus
                  className="w-full h-9 pl-8 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
              </div>
              {loading && <div className="flex justify-center py-4"><Loader2 size={16} className="animate-spin text-[#1E7C45]" /></div>}
              {!loading && query.length >= 2 && results.length === 0 && (
                <p className="text-sm text-[#9CA3AF] text-center py-4">No matches found</p>
              )}
              <div className="space-y-1.5 mb-3">
                {results.map(r => (
                  <div key={r.id} className="flex items-center justify-between p-2.5 rounded-md border border-[#E5E7EB] hover:border-[#D1D5DB]">
                    <div>
                      <p className="text-sm font-medium text-[#111827]">{r.recipe_name}</p>
                      <p className="text-xs text-[#9CA3AF]">
                        {Math.round(r.cal_per_serving)} kcal · {r.is_verified ? '✓ Verified' : 'Unverified'}
                      </p>
                    </div>
                    <button onClick={() => callPatch({ action: mode, replacement_food_id: r.id })}
                      disabled={submitting}
                      className="h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
                      Use
                    </button>
                  </div>
                ))}
              </div>
              <button onClick={() => setCustomMode(true)}
                className="w-full h-8 rounded-md border border-dashed border-[#D1D5DB] text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45]">
                Enter custom values instead
              </button>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-[#374151] mb-1">Dish Name *</label>
                  <input type="text" value={customForm.name}
                    onChange={e => setCustomForm(p => ({ ...p, name: e.target.value }))}
                    className="w-full h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
                </div>
                {(['calories', 'protein', 'carbs', 'fat', 'fiber'] as const).map((k, i) => (
                  <div key={k}>
                    <label className="block text-xs font-medium text-[#374151] mb-1">
                      {['Calories *', 'Protein g', 'Carbs g', 'Fat g', 'Fiber g'][i]}
                    </label>
                    <input type="number" min={0} value={customForm[k]}
                      onChange={e => setCustomForm(p => ({ ...p, [k]: e.target.value }))}
                      className="w-full h-8 px-2 rounded border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
                  </div>
                ))}
              </div>
              <label className="flex items-center gap-2 text-xs text-[#374151] mb-4 cursor-pointer">
                <input type="checkbox" checked={flagForDb} onChange={e => setFlagForDb(e.target.checked)}
                  className="rounded border-[#D1D5DB]" />
                Submit to recipe library (pending admin review)
              </label>
              <div className="flex gap-2">
                <button onClick={handleCustomSubmit} disabled={submitting}
                  className="flex items-center gap-1.5 h-8 px-4 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166634] disabled:opacity-50">
                  {submitting && <Loader2 size={11} className="animate-spin" />}
                  {mode === 'swap' ? 'Swap' : 'Add'}
                </button>
                <button onClick={() => setCustomMode(false)}
                  className="h-8 px-3 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151]">
                  Back to search
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── MealCard ──────────────────────────────────────────────────────────────
function MealCard({
  meal, patientId, onUpdated,
}: {
  meal: MealEntry;
  patientId: number;
  onUpdated: () => void;
}) {
  const [noteOpen,    setNoteOpen]    = useState(false);
  const [noteText,    setNoteText]    = useState(meal.doctor_note ?? '');
  const [saving,      setSaving]      = useState(false);
  const [removing,    setRemoving]    = useState(false);
  const [modalState,  setModalState]  = useState<null | { mode: 'swap' | 'add'; dishIndex: number }>(null);

  const dishes    = meal.dishes ?? [];
  const hasDishes = dishes.length > 0;

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

  const handleRemoveDish = async (dishIndex: number) => {
    setRemoving(true);
    try {
      await doctorApi.patchDish(patientId, meal.Date, meal['Meal Type'], dishIndex, { action: 'remove' });
      toast.success('Dish removed');
      onUpdated();
    } catch (err: any) {
      const d = err?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Failed to remove dish');
    } finally { setRemoving(false); }
  };

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 relative hover:border-[#D1D5DB] transition-colors">
      {/* Slot header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs font-medium uppercase tracking-wide text-[#6B7280]">
            {meal['Meal Type']}
          </span>
          <p className="text-xs text-[#9CA3AF]">{meal['Diet Type']}</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Session 22E (decision a): doctor-only generation-quality flag. Σ(scaled)
              vs the slot's generation-time target diverging >10% usually means a
              too-small/large dish was picked or the portion clamp maxed out. Not a
              patient-facing message. */}
          {(() => {
            const target = meal['Target Calories'];
            const provided = meal['Total Calories'] ?? 0;
            if (!target || target <= 0) return null;
            if (Math.abs(provided - target) / target <= 0.10) return null;
            return (
              <span
                title={`Plan provides ${Math.round(provided)} kcal, target was ${Math.round(target)} kcal — dish portion may be too small or large for this slot`}
                className="flex items-center text-[#D97706]"
              >
                <AlertCircle size={14} />
              </span>
            );
          })()}
          <MacroPill icon={<Flame size={11} />} value={meal['Total Calories']} unit="kcal" color="text-[#DC2626]" />
          <button
            onClick={() => { setNoteText(meal.doctor_note ?? ''); setNoteOpen(true); }}
            title="Add note"
            className="w-6 h-6 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#374151]"
          >
            <StickyNote size={12} />
          </button>
        </div>
      </div>

      {/* Per-dish cards or fallback for legacy (pre-Session-11) meals */}
      {hasDishes ? (
        <div className="space-y-2 mb-3">
          {dishes.map((dish, i) => (
            <DishCard
              key={i}
              dish={dish}
              index={i}
              onSwap={() => setModalState({ mode: 'swap', dishIndex: i })}
              onRemove={handleRemoveDish}
              removing={removing}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm font-medium text-[#111827] mb-3 leading-snug">
          {meal['Menu Names']}
        </p>
      )}

      {/* Macro summary row */}
      <div className="flex items-center gap-3 flex-wrap mb-3">
        <MacroPill icon={<Beef size={11} />}     value={meal['Total Protein']}  unit="g P"  color="text-[#2563EB]" />
        <MacroPill icon={<Wheat size={11} />}    value={meal['Total Carbs']}    unit="g C"  color="text-[#F59E0B]" />
        <MacroPill icon={<Droplets size={11} />} value={meal['Total Fat']}      unit="g F"  color="text-[#6B7280]" />
      </div>

      {hasDishes && (
        <button
          onClick={() => setModalState({ mode: 'add', dishIndex: -1 })}
          className="flex items-center gap-1.5 h-7 px-3 rounded-md border border-dashed border-[#D1D5DB] text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] w-full justify-center mb-2"
        >
          <Plus size={11} /> Add Dish
        </button>
      )}

      {meal.doctor_note && !noteOpen && (
        <div className="px-3 py-2 bg-[#F0FDF4] rounded-md border border-[#DCFCE7]">
          <p className="text-xs text-[#15803d] flex items-start gap-1.5">
            <StickyNote size={11} className="mt-0.5 flex-shrink-0" />
            <span>{meal.doctor_note}</span>
          </p>
        </div>
      )}

      {noteOpen && (
        <div className="mt-2">
          <textarea
            value={noteText}
            onChange={e => setNoteText(e.target.value)}
            rows={2}
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

      {modalState && (
        <RecipeSearchModal
          patientId={patientId}
          date={meal.Date}
          mealType={meal['Meal Type']}
          dishIndex={modalState.dishIndex}
          mode={modalState.mode}
          onClose={() => setModalState(null)}
          onSuccess={() => { onUpdated(); setModalState(null); }}
        />
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
    name: '', mealType: 'Breakfast', serving_weight_g: '', calories: '',
    protein: '', carbs: '', fat: '', fiber: '', diet_type: patientDietType,
  };

  const [form,          setForm]         = useState<CustomMealForm>(EMPTY_FORM);
  const [submitting,    setSubmitting]   = useState(false);
  const [geminiLoading, setGeminiLoading]= useState(false);
  const [showDropdown,  setShowDropdown] = useState(false);

  const { results: searchResults, loading: searchLoading } = useRecipeSearch(form.name);

  const handleSelectRecipe = (recipe: FoodItemSummary) => {
    setForm(p => ({
      ...p,
      name:             recipe.recipe_name,
      serving_weight_g: recipe.serving_weight_g !== null ? String(recipe.serving_weight_g) : '',
      calories:         String(recipe.cal_per_serving),
      protein:          String(recipe.protein_per_serving),
      carbs:            String(recipe.carbs_per_serving),
      fat:              String(recipe.fat_per_serving),
      fiber:            String(recipe.fiber_per_serving),
      diet_type:        recipe.diet_type,
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
      await doctorApi.addCustomDish(patientId, activeDate, form.mealType, {
        recipe_name: form.name.trim(),
        calories:    parseFloat(form.calories),
        protein:     parseFloat(form.protein) || 0,
        carbs:       parseFloat(form.carbs)   || 0,
        fat:         parseFloat(form.fat)     || 0,
        fiber:       parseFloat(form.fiber)   || 0,
        diet_type:   form.diet_type,
        slot_type:   inferSlotType(form.mealType),
      });
      queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) });
      toast.success(`"${form.name}" added to ${patientName}'s plan`);
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((e: any) => e.msg).join(', ')
        : typeof detail === 'string'
        ? detail
        : 'Failed to add meal';
      toast.error(message);
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

          {numField('serving_weight_g', 'Serving Weight (g) *')}
          {numField('calories', 'Calories (kcal) *')}
          {numField('protein',  'Protein (g)')}
          {numField('carbs',    'Carbs (g)')}
          {numField('fat',      'Fat (g)')}
          {numField('fiber',    'Fiber (g)')}
        </div>

        <div className="border border-[#E5E7EB] rounded-md px-3 py-2 mb-4 bg-[#F9FAFB] text-xs text-[#6B7280]">
          This meal is added directly to {patientName}'s plan. It is not saved to the recipe library.
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

// ── ComboDishSearchModal ──────────────────────────────────────────────────
function ComboDishSearchModal({ mealType, mode, onClose, onSelect }: {
  mealType: string;
  mode: 'swap' | 'add';
  onClose: () => void;
  onSelect: (fi: FoodItemSummary) => void;
}) {
  const [query, setQuery] = useState('');
  const { results, loading } = useRecipeSearch(query);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose}
        onKeyDown={e => e.key === 'Escape' && onClose()} role="button" tabIndex={-1} aria-label="Close" />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
          <p className="text-sm font-semibold text-[#111827]">
            {mode === 'swap' ? 'Swap Dish' : 'Add Dish'} — {mealType}
          </p>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={15} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <div className="relative mb-3">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
            <input type="text" value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Search recipes…" autoFocus
              className="w-full h-9 pl-8 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
          </div>
          {loading && <div className="flex justify-center py-4"><Loader2 size={16} className="animate-spin text-[#1E7C45]" /></div>}
          {!loading && query.length >= 2 && results.length === 0 && (
            <p className="text-sm text-[#9CA3AF] text-center py-4">No matches found</p>
          )}
          <div className="space-y-1.5">
            {results.map(r => (
              <div key={r.id} className="flex items-center justify-between p-2.5 rounded-md border border-[#E5E7EB] hover:border-[#D1D5DB]">
                <div>
                  <p className="text-sm font-medium text-[#111827]">{r.recipe_name}</p>
                  <p className="text-xs text-[#9CA3AF]">
                    {Math.round(r.cal_per_serving)} kcal · {r.is_verified ? '✓ Verified' : 'Unverified'}
                  </p>
                </div>
                <button onClick={() => onSelect(r)}
                  className="h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534]">
                  {mode === 'swap' ? 'Swap' : 'Add'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── ComboCard (v2 weekly plan) ────────────────────────────────────────────
function ComboCard({ combo, mealType, patientId, swapping, onSwap }: {
  combo: ComboEntry;
  mealType: string;
  patientId: number;
  swapping: boolean;
  onSwap: (comboId: number) => void;
}) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [searchTarget, setSearchTarget] = useState<{ dishIndex: number; action: 'swap' | 'add' } | null>(null);

  const dishEditMut = useMutation({
    mutationFn: ({ dishIndex, body }: {
      dishIndex: number;
      body: { action: 'swap' | 'add' | 'remove'; food_item_id?: number };
    }) => doctorApi.patchWeeklyDish(patientId, combo.combo_id, dishIndex, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.weeklyPlan(patientId) });
      setSearchTarget(null);
      toast.success('Dish updated');
    },
    onError: () => toast.error('Dish update failed'),
  });

  const dishNames = combo.dishes.length > 0
    ? combo.dishes.map(d => d.recipe_name).join(' + ')
    : combo.slot_composition;
  const slotTypes = [...new Set(combo.dishes.map(d => d.slot_type))];

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-[#6B7280] uppercase tracking-wide">
          Combo {combo.combo_index + 1}
        </span>
        <span className="flex items-center gap-1 text-[10px] text-[#DC2626]">
          <Flame size={9} />
          <span className="tabular-nums font-medium">{Math.round(combo.total_calories)}</span>
          <span className="text-[#9CA3AF]">kcal</span>
        </span>
      </div>

      {!expanded ? (
        <>
          <p
            className="text-xs font-medium text-[#111827] leading-snug flex-1 cursor-pointer hover:text-[#1E7C45]"
            onClick={() => setExpanded(true)}
          >
            {dishNames}
          </p>
          <div className="flex flex-wrap gap-1">
            {slotTypes.map(t => (
              <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#F3F4F6] text-[#6B7280]">{t}</span>
            ))}
          </div>
          <button
            onClick={() => onSwap(combo.combo_id)}
            disabled={swapping}
            className="mt-1 flex items-center justify-center gap-1.5 h-7 rounded-md border border-[#D1D5DB] text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45] disabled:opacity-50 transition-colors"
          >
            {swapping ? <Loader2 size={11} className="animate-spin" /> : <ArrowLeftRight size={11} />}
            Swap
          </button>
        </>
      ) : (
        <>
          <div className="flex flex-col gap-1.5 mt-1">
            {combo.dishes.map((dish, idx) => (
              <div key={idx} className="flex items-center gap-1.5 text-xs">
                <span className="flex-1 text-[#111827] truncate leading-snug">{dish.recipe_name}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-[#F3F4F6] text-[#6B7280] shrink-0">{dish.slot_type}</span>
                <button
                  onClick={() => setSearchTarget({ dishIndex: idx, action: 'swap' })}
                  disabled={dishEditMut.isPending}
                  className="p-0.5 rounded hover:bg-[#F3F4F6] text-[#6B7280] hover:text-[#1E7C45] disabled:opacity-50 shrink-0"
                  title="Swap dish"
                >
                  <ArrowLeftRight size={11} />
                </button>
                <button
                  onClick={() => {
                    if (combo.dishes.length <= 1) { toast.error('Cannot remove last dish'); return; }
                    dishEditMut.mutate({
                      dishIndex: idx,
                      body: { action: 'remove', food_item_id: dish.food_id ?? undefined },
                    });
                  }}
                  disabled={dishEditMut.isPending}
                  className="p-0.5 rounded hover:bg-[#FEE2E2] text-[#6B7280] hover:text-[#DC2626] disabled:opacity-50 shrink-0"
                  title="Remove dish"
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() => setSearchTarget({ dishIndex: -1, action: 'add' })}
            className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline mt-0.5"
          >
            <Plus size={11} /> Add Dish
          </button>
          <button
            onClick={() => setExpanded(false)}
            className="mt-1 flex items-center justify-center h-7 rounded-md border border-[#D1D5DB] text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45]"
          >
            Done
          </button>
        </>
      )}

      {searchTarget && (
        <ComboDishSearchModal
          mealType={mealType}
          mode={searchTarget.action}
          onClose={() => setSearchTarget(null)}
          onSelect={(fi) => dishEditMut.mutate({
            dishIndex: searchTarget.dishIndex,
            body: { action: searchTarget.action, food_item_id: fi.id },
          })}
        />
      )}
    </div>
  );
}

// ── AddCustomMealModal (v2) ───────────────────────────────────────────────
function AddCustomMealModal({ patientId, activeDate, mealType, combos, onClose, onSuccess }: {
  patientId: number;
  activeDate: string;
  mealType: string;
  combos: ComboEntry[];
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [tab, setTab] = useState<'library' | 'custom'>('library');
  const [comboIndex, setComboIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState('');
  const [customName, setCustomName] = useState('');
  const [customCal, setCustomCal] = useState('');
  const { results, loading } = useRecipeSearch(query);

  const handleLibrarySelect = async (fi: FoodItemSummary) => {
    const comboId = combos[comboIndex]?.combo_id;
    if (!comboId) return;
    setSubmitting(true);
    try {
      await doctorApi.patchWeeklyDish(patientId, comboId, 0, { action: 'add', food_item_id: fi.id });
      toast.success('Dish added');
      onSuccess();
    } catch {
      toast.error('Failed to add dish');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCustomAdd = async () => {
    if (!customName.trim() || !customCal) { toast.error('Name and calories required'); return; }
    setSubmitting(true);
    try {
      await doctorApi.addCustomDish(patientId, activeDate, mealType, {
        recipe_name: customName.trim(),
        calories: parseFloat(customCal),
        protein: 0,
        carbs: 0,
        fat: 0,
        fiber: 0,
        combo_index: comboIndex,
      });
      toast.success('Custom dish added');
      onSuccess();
    } catch {
      toast.error('Failed to add custom dish');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose}
        onKeyDown={e => e.key === 'Escape' && onClose()} role="button" tabIndex={-1} aria-label="Close" />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
          <p className="text-sm font-semibold text-[#111827]">Add Custom Meal — {mealType}</p>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={15} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {/* Combo selector */}
          <div className="mb-3">
            <p className="text-xs text-[#6B7280] mb-1.5">Add to combo</p>
            <div className="flex gap-2 flex-wrap">
              {combos.map((c, i) => (
                <button
                  key={c.combo_id}
                  onClick={() => setComboIndex(i)}
                  className={`h-7 px-3 rounded-md text-xs border transition-colors ${
                    comboIndex === i
                      ? 'bg-[#1E7C45] text-white border-[#1E7C45]'
                      : 'border-[#D1D5DB] text-[#374151] hover:border-[#1E7C45]'
                  }`}
                >
                  Combo {i + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Tab toggle */}
          <div className="flex gap-1 mb-3 p-1 bg-[#F3F4F6] rounded-lg">
            {(['library', 'custom'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 h-7 rounded-md text-xs font-medium transition-colors ${
                  tab === t ? 'bg-white text-[#111827] shadow-sm' : 'text-[#6B7280]'
                }`}
              >
                {t === 'library' ? 'From Library' : 'Custom'}
              </button>
            ))}
          </div>

          {tab === 'library' ? (
            <>
              <div className="relative mb-3">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
                <input type="text" value={query} onChange={e => setQuery(e.target.value)}
                  placeholder="Search recipes…" autoFocus
                  className="w-full h-9 pl-8 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
              </div>
              {loading && <div className="flex justify-center py-4"><Loader2 size={16} className="animate-spin text-[#1E7C45]" /></div>}
              {!loading && query.length >= 2 && results.length === 0 && (
                <p className="text-sm text-[#9CA3AF] text-center py-4">No matches found</p>
              )}
              <div className="space-y-1.5">
                {results.map(r => (
                  <div key={r.id} className="flex items-center justify-between p-2.5 rounded-md border border-[#E5E7EB] hover:border-[#D1D5DB]">
                    <div>
                      <p className="text-sm font-medium text-[#111827]">{r.recipe_name}</p>
                      <p className="text-xs text-[#9CA3AF]">{Math.round(r.cal_per_serving)} kcal · {r.is_verified ? '✓ Verified' : 'Unverified'}</p>
                    </div>
                    <button onClick={() => handleLibrarySelect(r)} disabled={submitting}
                      className="h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
                      Add
                    </button>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="space-y-3">
              <input
                className="w-full h-8 px-3 rounded-md border border-[#D1D5DB] text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                placeholder="Dish name *"
                value={customName}
                onChange={e => setCustomName(e.target.value)}
              />
              <input
                type="number"
                min={1}
                className="w-full h-8 px-3 rounded-md border border-[#D1D5DB] text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                placeholder="Calories *"
                value={customCal}
                onChange={e => setCustomCal(e.target.value)}
              />
              <button
                onClick={handleCustomAdd}
                disabled={submitting}
                className="w-full h-9 rounded-md bg-[#1E7C45] text-white text-sm font-medium hover:bg-[#166634] disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting && <Loader2 size={13} className="animate-spin" />}
                Add Dish
              </button>
            </div>
          )}
        </div>
      </div>
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
  const [addCustomFor,   setAddCustomFor]    = useState<{ mealType: string; combos: ComboEntry[] } | null>(null);
  const mealTypes = getMealTypes();

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

  const { data: weeklyPlan } = useQuery({
    queryKey: qk.weeklyPlan(patientId),
    queryFn: () => doctorApi.getWeeklyPlan(patientId),
  });

  const swapMut = useMutation({
    mutationFn: (comboId: number) => doctorApi.swapCombo(patientId, comboId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.weeklyPlan(patientId) });
      toast.success('Combo swapped');
    },
    onError: (err: any) => {
      const status = err?.response?.status;
      if (status === 409) toast.error('No dishes available for this slot — pool exhausted');
      else if (status === 404) toast.error('Combo not found');
      else toast.error('Swap failed — please try again');
    },
  });

  const approveMut = useMutation({
    mutationFn: () => doctorApi.approveWeeklyPlan(patientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.weeklyPlan(patientId) });
      toast.success('Plan approved — patient can now view it');
    },
    onError: () => toast.error('Approval failed'),
  });

  if (isLoading) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
    </div>
  );

  const isV2 = !!weeklyPlan && weeklyPlan.combos_available !== false;

  if (!isV2 && (isError || !plan)) return (
    <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
      <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
      <p className="text-base font-medium text-[#374151]">No active plan</p>
      <p className="text-sm text-[#6B7280] mt-1">
        {patientName} doesn't have an active meal plan yet.
      </p>
    </div>
  );

  const grouped  = groupByDate(plan?.meals ?? []);
  const v1Dates  = Object.keys(grouped).sort();
  const v2Dates  = isV2 ? Object.keys(weeklyPlan.plan).sort() : [];
  const dates    = isV2 ? v2Dates : v1Dates;

  if (dates.length === 0) return (
    <div className="max-w-4xl bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
      <CalendarDays size={36} className="text-[#D1D5DB] mx-auto mb-3" />
      <p className="text-base font-medium text-[#374151]">Plan has no meals yet</p>
    </div>
  );

  const activeDate = dates[activeDateIdx] ?? dates[0];

  // v1-only day data
  const allDayMeals = !isV2 ? (grouped[activeDate] ?? []) : [];
  const dayMeals    = allDayMeals.filter(m => mealTypes.includes(m['Meal Type']));
  const totalCalories = dayMeals.reduce((s, m) => s + (m['Total Calories'] ?? 0), 0);
  const totalProtein  = dayMeals.reduce((s, m) => s + (m['Total Protein']  ?? 0), 0);
  const totalCarbs    = dayMeals.reduce((s, m) => s + (m['Total Carbs']    ?? 0), 0);
  const totalFat      = dayMeals.reduce((s, m) => s + (m['Total Fat']      ?? 0), 0);

  return (
    <div className="max-w-4xl">
      {/* Plan-level doctor notes */}
      {plan?.doctor_notes && !editingNotes && (
        <div className="mb-5 px-4 py-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-[#15803d]">Doctor Notes</p>
            <button
              onClick={() => { setNotesValue(plan?.doctor_notes ?? ''); setEditingNotes(true); }}
              className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline"
            >
              <Pencil size={11} /> Edit
            </button>
          </div>
          <p className="text-sm text-[#374151]">{plan?.doctor_notes}</p>
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
      {!plan?.doctor_notes && !editingNotes && (
        <button
          onClick={() => { setNotesValue(''); setEditingNotes(true); }}
          className="flex items-center gap-2 h-8 px-3 mb-4 rounded-md border
                     border-dashed border-[#D1D5DB] text-xs text-[#6B7280]
                     hover:border-[#1E7C45] hover:text-[#1E7C45]"
        >
          <Pencil size={12} /> Add doctor notes to this plan
        </button>
      )}

      {/* v2 approval controls */}
      {isV2 && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {weeklyPlan.approval_status === 'draft' ? (
            <button
              onClick={() => approveMut.mutate()}
              disabled={approveMut.isPending}
              className="flex items-center gap-2 h-9 px-5 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166634] disabled:opacity-50"
            >
              {approveMut.isPending && <Loader2 size={13} className="animate-spin" />}
              Approve Week
            </button>
          ) : (
            <span className="flex items-center gap-1.5 text-sm text-[#15803d] font-medium">
              <CalendarDays size={14} /> Plan approved — visible to patient
            </span>
          )}
        </div>
      )}

      <DaySelector dates={dates} activeDateIdx={activeDateIdx} onSelect={setActiveDateIdx} />

      {/* Day heading + totals */}
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[#111827]">
            {activeDate} — Meal Plan
          </h2>
          <p className="text-sm text-[#6B7280]">
            {isV2 ? '4 combos per slot · v2 plan' : `${dayMeals.length} meals · ${patientMealsPerDay}-meal plan`}
          </p>
        </div>
        {!isV2 && (
          <div className="flex items-center gap-4 text-sm">
            <span className="text-[#6B7280]">Day total:</span>
            <span className="font-semibold text-[#111827] tabular-nums">
              {Math.round(totalCalories)} kcal
            </span>
            <span className="text-xs text-[#9CA3AF]">
              P:{Math.round(totalProtein)}g · C:{Math.round(totalCarbs)}g · F:{Math.round(totalFat)}g
            </span>
          </div>
        )}
      </div>

      {isV2 ? (
        /* v2 combo grid — one section per meal type */
        <div className="space-y-6">
          {Object.entries(weeklyPlan.plan[activeDate] ?? {}).map(([mealType, combos]) => (
            <div key={mealType}>
              <h3 className="text-sm font-semibold text-[#374151] mb-3 uppercase tracking-wide">
                {mealType}
              </h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {combos.map(combo => (
                  <ComboCard
                    key={combo.combo_id}
                    combo={combo}
                    mealType={mealType}
                    patientId={patientId}
                    swapping={swapMut.isPending && swapMut.variables === combo.combo_id}
                    onSwap={(id) => swapMut.mutate(id)}
                  />
                ))}
              </div>
              <button
                onClick={() => setAddCustomFor({ mealType, combos })}
                className="mt-2 flex items-center gap-2 h-8 px-3 rounded-md border border-dashed border-[#D1D5DB] text-xs text-[#6B7280] hover:border-[#1E7C45] hover:text-[#1E7C45] w-full justify-center transition-colors"
              >
                <Plus size={12} /> Add Custom Meal
              </button>
            </div>
          ))}
        </div>
      ) : (
        /* v1 view — existing meal cards */
        <>
          <TdeeProgressBar totalCalories={totalCalories} patientTdee={patientTdee} patientMealsPerDay={patientMealsPerDay} />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            {dayMeals.map((meal, i) => (
              <MealCard
                key={`${meal.Date}-${meal['Meal Type']}`}
                meal={meal}
                patientId={patientId}
                onUpdated={() =>
                  queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) })
                }
              />
            ))}
          </div>

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
        </>
      )}

      {addCustomFor && (
        <AddCustomMealModal
          patientId={patientId}
          activeDate={activeDate}
          mealType={addCustomFor.mealType}
          combos={addCustomFor.combos}
          onClose={() => setAddCustomFor(null)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: qk.weeklyPlan(patientId) });
            setAddCustomFor(null);
          }}
        />
      )}
    </div>
  );
}
