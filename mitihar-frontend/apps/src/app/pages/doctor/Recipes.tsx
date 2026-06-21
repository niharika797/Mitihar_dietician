import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Plus, Search, ChefHat, Flame, Beef, Wheat, Sparkles,
  Loader2, X, AlertCircle, UserPlus, Calendar, Check,
} from 'lucide-react';
import apiClient from '../../../lib/axios';
import { doctorApi, FoodItemSummary, PatientSummary } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';

const AVOID_TAGS = [
  "avoid_diabetes","avoid_hypertension","avoid_highchol","avoid_pcos",
  "avoid_hypothyroid","avoid_hyperthyroid","avoid_heart","avoid_kidney",
  "avoid_fattyliver","avoid_ibs","avoid_gluten","avoid_gout",
];
const PREFER_TAGS = [
  "diabetes_friendly","heart_friendly","cholesterol_friendly","pcos_friendly",
  "thyroid_support","liver_friendly","gut_friendly","gluten_free",
  "calcium_rich","iron_rich",
];
const formatTag = (tag: string) =>
  tag.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());

// ── Assign Recipe Modal ──────────────────────────────────────────────────────────
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

interface AssignModalProps {
  recipe: FoodItemSummary;
  onClose: () => void;
}

function AssignModal({ recipe, onClose }: AssignModalProps) {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mealType, setMealType]       = useState('Breakfast');
  const [mealDate, setMealDate]       = useState(() => todayStr());
  const [note, setNote]               = useState('');

  const { data: patients = [], isLoading: patientsLoading } = useQuery({
    queryKey: ['doctor', 'all-patients'],
    queryFn:  doctorApi.listAllPatients,
    staleTime: 2 * 60 * 1000,
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      doctorApi.assignRecipe(recipe.id, {
        patient_ids: selectedIds,
        meal_type:   mealType,
        meal_date:   mealDate,
        note:        note || undefined,
      }),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['doctor', 'patient'] });
      toast.success(
        data.updated_count
          ? `Assigned to ${data.updated_count} patient${data.updated_count > 1 ? 's' : ''}`
          : 'No patients updated — they may not have an active plan',
      );
      onClose();
    },
    onError: () => toast.error('Failed to assign recipe'),
  });

  const toggle = (id: number) =>
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id],
    );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} onKeyDown={(e) => e.key === "Escape" && onClose()} role="button" aria-label="Close dialog" tabIndex={0} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-[#E5E7EB]">
          <div>
            <p className="text-base font-semibold text-[#111827]">Assign Recipe</p>
            <p className="text-sm text-[#6B7280] mt-0.5 line-clamp-1">{recipe.recipe_name}</p>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-5 flex-1">
          {/* Patients */}
          <p className="text-xs font-medium text-[#374151] mb-2">
            Select Patients <span className="text-[#DC2626]">*</span>
          </p>
          {patientsLoading ? (
            <div className="flex justify-center py-6">
              <Loader2 size={20} className="animate-spin text-[#1E7C45]" />
            </div>
          ) : patients.length === 0 ? (
            <p className="text-sm text-[#9CA3AF] text-center py-4">No patients found</p>
          ) : (
            <div className="border border-[#E5E7EB] rounded-lg overflow-hidden mb-4 max-h-40 overflow-y-auto">
              {patients.map((p: PatientSummary) => (
                <label
                  key={p.id}
                  className="flex items-center gap-3 px-3 py-2.5 hover:bg-[#F9FAFB] cursor-pointer border-b border-[#F3F4F6] last:border-0"
                >
                  <div className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                    selectedIds.includes(p.id)
                      ? 'bg-[#1E7C45] border-[#1E7C45]'
                      : 'border-[#D1D5DB]'
                  }`}>
                    {selectedIds.includes(p.id) && <Check size={10} className="text-white" />}
                  </div>
                  <input type="checkbox" className="hidden" checked={selectedIds.includes(p.id)} onChange={() => toggle(p.id)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[#111827] truncate">{p.name}</p>
                    <p className="text-xs text-[#9CA3AF] truncate">{p.email}</p>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    p.subscription_status === 'active'
                      ? 'bg-[#DCFCE7] text-[#15803d]'
                      : 'bg-[#F3F4F6] text-[#6B7280]'
                  }`}>{p.subscription_status}</span>
                </label>
              ))}
            </div>
          )}

          {/* Meal type */}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label htmlFor="assign-meal-type" className="block text-xs font-medium text-[#374151] mb-1.5">Meal Type</label>
              <select
                id="assign-meal-type"
                value={mealType}
                onChange={e => setMealType(e.target.value)}
                className="w-full h-9 px-2 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
              >
                {['Breakfast', 'Lunch', 'Dinner'].map(t => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="assign-date" className="block text-xs font-medium text-[#374151] mb-1.5">
                <span className="flex items-center gap-1"><Calendar size={11} /> Date</span>
              </label>
              <input
                id="assign-date"
                type="date"
                value={mealDate}
                onChange={e => setMealDate(e.target.value)}
                className="w-full h-9 px-2 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
              />
            </div>
          </div>

          {/* Optional note */}
          <div>
            <label htmlFor="assign-note" className="block text-xs font-medium text-[#374151] mb-1.5">Note for Patient (optional)</label>
            <input
              id="assign-note"
              type="text"
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. Take with warm water"
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 p-5 border-t border-[#E5E7EB]">
          <p className="text-xs text-[#9CA3AF]">
            {selectedIds.length > 0 ? `${selectedIds.length} patient${selectedIds.length > 1 ? 's' : ''} selected` : 'No patients selected'}
          </p>
          <div className="flex gap-2">
            <button onClick={onClose} className="h-9 px-4 rounded-md border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]">
              Cancel
            </button>
            <button
              onClick={() => assignMutation.mutate()}
              disabled={selectedIds.length === 0 || !mealDate || assignMutation.isPending}
              className="flex items-center gap-1.5 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50 transition-colors"
            >
              {assignMutation.isPending
                ? <Loader2 size={14} className="animate-spin" />
                : <UserPlus size={14} />}
              Assign
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── TagEditPanel ───────────────────────────────────────────────────────────────
interface TagEditPanelProps {
  recipe: FoodItemSummary;
  onSave: (updated: FoodItemSummary) => void;
  onClose: () => void;
}

function TagEditPanel({ recipe, onSave, onClose }: TagEditPanelProps) {
  const queryClient = useQueryClient();
  const [draftAvoid, setDraftAvoid] = useState<Set<string>>(new Set(recipe.avoid_tags));
  const [draftPrefer, setDraftPrefer] = useState<Set<string>>(new Set(recipe.prefer_tags));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const toggleAvoid = (tag: string) =>
    setDraftAvoid(prev => {
      const next = new Set(prev);
      next.has(tag) ? next.delete(tag) : next.add(tag);
      return next;
    });

  const togglePrefer = (tag: string) =>
    setDraftPrefer(prev => {
      const next = new Set(prev);
      next.has(tag) ? next.delete(tag) : next.add(tag);
      return next;
    });

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const updated = await doctorApi.patchRecipeTags(recipe.id, {
        avoid_tags: [...draftAvoid],
        prefer_tags: [...draftPrefer],
      });
      onSave({ ...recipe, avoid_tags: updated.avoid_tags, prefer_tags: updated.prefer_tags });
      queryClient.invalidateQueries({ queryKey: ['doctor', 'recipes'] });
    } catch (err: any) {
      setError(
        err?.response?.status === 422
          ? (err?.response?.data?.detail ?? 'Invalid tags.')
          : 'Failed to save tags.',
      );
      setSaving(false);
    }
  };

  return (
    <div className="mt-3 p-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-medium text-[#DC2626] mb-2">Avoid Tags</p>
          <div className="flex flex-wrap gap-1">
            {AVOID_TAGS.map(tag => (
              <button
                key={tag}
                type="button"
                onClick={() => toggleAvoid(tag)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors ${
                  draftAvoid.has(tag)
                    ? 'bg-[#FEE2E2] border-[#FCA5A5] text-[#DC2626]'
                    : 'bg-white border-[#E5E7EB] text-[#9CA3AF] hover:border-[#FCA5A5]'
                }`}
              >
                {formatTag(tag)}
              </button>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-medium text-[#16A34A] mb-2">Prefer Tags</p>
          <div className="flex flex-wrap gap-1">
            {PREFER_TAGS.map(tag => (
              <button
                key={tag}
                type="button"
                onClick={() => togglePrefer(tag)}
                className={`text-[10px] px-2 py-0.5 rounded-full border transition-colors ${
                  draftPrefer.has(tag)
                    ? 'bg-[#DCFCE7] border-[#86EFAC] text-[#16A34A]'
                    : 'bg-white border-[#E5E7EB] text-[#9CA3AF] hover:border-[#86EFAC]'
                }`}
              >
                {formatTag(tag)}
              </button>
            ))}
          </div>
        </div>
      </div>
      {error && <p className="text-xs text-[#DC2626] mt-2">{error}</p>}
      <div className="flex gap-2 mt-3 justify-end">
        <button
          type="button"
          onClick={onClose}
          className="h-7 px-3 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:bg-white"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1 h-7 px-3 rounded bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50"
        >
          {saving && <Loader2 size={10} className="animate-spin" />}
          Save
        </button>
      </div>
    </div>
  );
}

const MEAL_TIMES = ['All', 'Breakfast', 'Lunch', 'Dinner'];
const VERIFIED_OPTIONS = ['All', 'Verified', 'Unverified'] as const;
type VerifiedFilter = typeof VERIFIED_OPTIONS[number];

interface AiEstimate {
  dish_name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  cuisine: string;
  serving_description: string;
}

interface AddForm {
  recipe_name: string;
  slot_type: string;
  calories: string;
  protein: string;
  carbs: string;
  fat: string;
  fiber: string;
  amount_g: string;
  sodium: string;
  diet_type: string;
  meal_time: string;
  region: string;
}

const EMPTY_FORM: AddForm = {
  recipe_name: '',
  slot_type: 'main_dish',
  calories: '',
  protein: '',
  carbs: '',
  fat: '',
  fiber: '',
  amount_g: '',
  sodium: '',
  diet_type: 'Vegetarian',
  meal_time: 'Breakfast',
  region: '',
};


// ── RecipeCard ─────────────────────────────────────────────────────────────────
interface RecipeCardProps {
  recipe: FoodItemSummary;
  onAssign: (recipe: FoodItemSummary) => void;
}

function RecipeCard({ recipe, onAssign }: RecipeCardProps) {
  const [localRecipe, setLocalRecipe] = useState<FoodItemSummary>(recipe);
  const [showTagEdit, setShowTagEdit] = useState(false);

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 hover:border-[#D1D5DB] transition-colors flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <span className="text-xs text-[#6B7280]">{localRecipe.slot_type} · {localRecipe.diet_type}</span>
          <p className="text-sm font-medium text-[#111827] mt-0.5">{localRecipe.recipe_name}</p>
        </div>
        {localRecipe.is_verified ? (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#DCFCE7] text-[#15803d] border border-[#BBF7D0] flex-shrink-0 ml-2">
            Verified
          </span>
        ) : (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#F3F4F6] text-[#6B7280] border border-[#E5E7EB] flex-shrink-0 ml-2">
            Unverified
          </span>
        )}
      </div>
      {localRecipe.meal_time_tags.length > 0 && (
        <div className="flex gap-1 mb-2 flex-wrap">
          {localRecipe.meal_time_tags.map(t => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-[#F3F4F6] text-[#6B7280]">{t}</span>
          ))}
        </div>
      )}
      {localRecipe.avoid_tags.length > 0 && (
        <div className="flex gap-1 mb-1 flex-wrap">
          {localRecipe.avoid_tags.map(t => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#FEE2E2] text-[#DC2626]">{formatTag(t)}</span>
          ))}
        </div>
      )}
      {localRecipe.prefer_tags.length > 0 && (
        <div className="flex gap-1 mb-1 flex-wrap">
          {localRecipe.prefer_tags.map(t => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#DCFCE7] text-[#16A34A]">{formatTag(t)}</span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 mt-3 flex-wrap">
        <span className="flex items-center gap-1 text-xs text-[#DC2626]">
          <Flame size={11} /><span className="tabular-nums font-medium">{Math.round(localRecipe.cal_per_serving)}</span> kcal
        </span>
        <span className="flex items-center gap-1 text-xs text-[#2563EB]">
          <Beef size={11} /><span className="tabular-nums font-medium">{localRecipe.protein_per_serving.toFixed(1)}g</span> P
        </span>
        <span className="flex items-center gap-1 text-xs text-[#F59E0B]">
          <Wheat size={11} /><span className="tabular-nums font-medium">{localRecipe.carbs_per_serving.toFixed(1)}g</span> C
        </span>
      </div>
      <div className="flex items-center justify-between mt-3">
        <p className="text-xs text-[#9CA3AF]">Source: {localRecipe.source}</p>
        <div className="flex gap-1.5">
          <button
            onClick={() => setShowTagEdit(p => !p)}
            className="h-7 px-2.5 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45] hover:bg-[#F0FDF4] transition-colors"
          >
            {showTagEdit ? 'Close' : 'Edit Tags'}
          </button>
          {localRecipe.is_verified && (
            <button onClick={() => onAssign(localRecipe)}
              className="flex items-center gap-1 h-7 px-2.5 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45] hover:bg-[#F0FDF4] transition-colors">
              <UserPlus size={11} /> Assign
            </button>
          )}
        </div>
      </div>
      {showTagEdit && (
        <TagEditPanel
          recipe={localRecipe}
          onSave={(updated) => { setLocalRecipe(updated); setShowTagEdit(false); }}
          onClose={() => setShowTagEdit(false)}
        />
      )}
    </div>
  );
}

// ── AddRecipeForm ──────────────────────────────────────────────────────────────
interface AddRecipeFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

function AddRecipeForm({ onSuccess, onCancel }: AddRecipeFormProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AddForm>(EMPTY_FORM);
  const [nameInput, setNameInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiEstimate, setAiEstimate] = useState<AiEstimate | null>(null);
  const [aiError, setAiError] = useState('');
  const [aiHighlighted, setAiHighlighted] = useState(false);

  const addMutation = useMutation({
    mutationFn: () => doctorApi.addRecipe({
      recipe_name: form.recipe_name, slot_type: form.slot_type,
      cal_per_serving: Number(form.calories), protein_per_serving: Number(form.protein),
      carbs_per_serving: Number(form.carbs), fat_per_serving: Number(form.fat),
      fiber_per_serving: Number(form.fiber) || 0,
      serving_weight_g: Number(form.amount_g),
      sodium_per_serving: form.sodium ? Number(form.sodium) : undefined,
      diet_type: form.diet_type,
      meal_time_tags: form.meal_time ? [form.meal_time] : [], plan_type_tags: ['Healthy'],
      ingredients: [], region_tags: form.region ? [form.region] : [],
      submit_to_global: false,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor', 'recipes'] });
      toast.success('Recipe added — pending admin approval');
      onSuccess();
    },
    onError: () => toast.error('Failed to add recipe'),
  });

  const handleNameChange = (val: string) => {
    setNameInput(val);
    setForm(p => ({ ...p, recipe_name: val }));
    setAiEstimate(null); setAiError(''); setAiHighlighted(false);
  };

  const handleEstimate = async () => {
    if (!nameInput.trim()) return;
    setAiLoading(true); setAiError(''); setAiEstimate(null);
    try {
      const { data } = await apiClient.post<AiEstimate & { ai_estimated: boolean }>(
        '/doctor/recipes/estimate', { dish_name: nameInput.trim() },
      );
      setAiEstimate(data); setAiHighlighted(true);
      setForm(p => ({ ...p, recipe_name: data.dish_name || p.recipe_name,
        calories: String(data.calories), protein: String(data.protein),
        carbs: String(data.carbs), fat: String(data.fat),
      }));
    } catch (err: any) {
      setAiError(err?.response?.data?.detail ?? 'Could not estimate nutrition. Please fill in values manually.');
    } finally { setAiLoading(false); }
  };

  const macroInputClass = (highlighted: boolean) =>
    `w-full h-10 px-3 rounded-md border text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent transition-colors ${
      highlighted ? 'border-[#F59E0B] bg-[#FFFBEB]' : 'border-[#D1D5DB] bg-white'
    }`;

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 mb-6">
      <h2 className="text-base font-medium text-[#111827] mb-4">Add Recipe to Library</h2>
      <form onSubmit={(e) => { e.preventDefault(); addMutation.mutate(); }} className="max-w-xl">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="col-span-2">
            <label htmlFor="recipe-name" className="block text-sm font-medium text-[#374151] mb-1.5">
              Recipe Name <span className="text-[#DC2626] ml-0.5">*</span>
            </label>
            <input id="recipe-name" required value={nameInput} onChange={e => handleNameChange(e.target.value)}
              placeholder="e.g. Moong Dal Cheela"
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent" />
            {nameInput.trim().length >= 2 && !aiEstimate && (
              <div className="mt-2 flex items-center gap-2">
                <button type="button" onClick={handleEstimate} disabled={aiLoading}
                  className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#D1D5DB] text-xs font-medium text-[#374151] hover:bg-[#F9FAFB] transition-colors disabled:opacity-50">
                  {aiLoading ? <><Loader2 size={12} className="animate-spin" /> Estimating…</> : <><Sparkles size={12} className="text-[#F59E0B]" /> Estimate with AI</>}
                </button>
                {aiError && <p className="text-xs text-[#DC2626]">{aiError}</p>}
              </div>
            )}
            {aiEstimate && (
              <div className="mt-2 flex items-start gap-2 px-3 py-2 bg-[#FFFBEB] border border-[#FDE68A] rounded-md">
                <Sparkles size={13} className="text-[#F59E0B] mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[#92400E]">AI estimate applied — please verify before saving</p>
                  {aiEstimate.serving_description && <p className="text-xs text-[#B45309] mt-0.5">Serving: {aiEstimate.serving_description}</p>}
                </div>
                <button type="button" onClick={() => { setAiEstimate(null); setAiHighlighted(false); }} className="text-[#9CA3AF] hover:text-[#374151]">
                  <X size={12} />
                </button>
              </div>
            )}
          </div>
          <div>
            <label htmlFor="recipe-slot" className="block text-sm font-medium text-[#374151] mb-1.5">Slot Type</label>
            <select id="recipe-slot" value={form.slot_type} onChange={e => setForm(p => ({ ...p, slot_type: e.target.value }))}
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
              {['grain','dal_protein','main_dish','sabzi','beverage','snack','fruit','egg_dish'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="recipe-diet" className="block text-sm font-medium text-[#374151] mb-1.5">Diet Type</label>
            <select id="recipe-diet" value={form.diet_type} onChange={e => setForm(p => ({ ...p, diet_type: e.target.value }))}
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
              {['Vegetarian','Non-Vegetarian','Eggetarian'].map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="recipe-meal-time" className="block text-sm font-medium text-[#374151] mb-1.5">Meal Time</label>
            <select id="recipe-meal-time" value={form.meal_time} onChange={e => setForm(p => ({ ...p, meal_time: e.target.value }))}
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
              {['Breakfast','Lunch','Dinner'].map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="recipe-region" className="block text-sm font-medium text-[#374151] mb-1.5">Region</label>
            <input id="recipe-region" value={form.region} onChange={e => setForm(p => ({ ...p, region: e.target.value }))} placeholder="e.g. South Indian"
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
          </div>
          {(['calories','protein','carbs','fat','fiber'] as const).map((key, i) => (
            <div key={key}>
              <label htmlFor={`recipe-${key}`} className="block text-sm font-medium text-[#374151] mb-1.5">
                {['Calories (kcal) *','Protein (g) *','Carbs (g) *','Fat (g) *','Fiber (g)'][i]}
              </label>
              <input id={`recipe-${key}`} required={key !== 'fiber'} type="number" min={0} value={form[key]}
                onChange={e => { setForm(p => ({ ...p, [key]: e.target.value })); setAiHighlighted(false); }}
                placeholder="0" className={macroInputClass(aiHighlighted && key !== 'fiber')} />
            </div>
          ))}
          <div>
            <label htmlFor="recipe-amount-g" className="block text-sm font-medium text-[#374151] mb-1.5">
              Serving Size (grams) <span className="text-[#DC2626] ml-0.5">*</span>
            </label>
            <input id="recipe-amount-g" required type="number" min={1} value={form.amount_g}
              onChange={e => setForm(p => ({ ...p, amount_g: e.target.value }))}
              placeholder="e.g. 150"
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent" />
          </div>
          <div>
            <label htmlFor="recipe-sodium" className="block text-sm font-medium text-[#374151] mb-1.5">
              Sodium (mg per serving)
            </label>
            <input id="recipe-sodium" type="number" min={0} value={form.sodium}
              onChange={e => setForm(p => ({ ...p, sodium: e.target.value }))}
              placeholder="0"
              className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent" />
          </div>
        </div>
        <div className="flex gap-3">
          <button type="submit" disabled={addMutation.isPending}
            className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50 flex items-center gap-2">
            {addMutation.isPending && <Loader2 size={13} className="animate-spin" />}
            Add to Recipe Library
          </button>
          <button type="button" onClick={onCancel}
            className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB] transition-colors">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
export function Recipes() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [mealTimeFilter, setMealTimeFilter] = useState('All');
  const [verifiedFilter, setVerifiedFilter] = useState<VerifiedFilter>('All');
  const [showAddForm, setShowAddForm] = useState(false);
  const [assignRecipe, setAssignRecipe] = useState<FoodItemSummary | null>(null);

  // Debounce search
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearch = (val: string) => {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(val), 350);
  };

  // Query params object — drives cache key
  const queryParams = {
    ...(debouncedSearch.trim() ? { search: debouncedSearch.trim() } : {}),
    ...(mealTimeFilter !== 'All' ? { meal_time: mealTimeFilter } : {}),
    ...(verifiedFilter !== 'All' ? { is_verified: verifiedFilter === 'Verified' } : {}),
  };

  const { data: recipes = [], isLoading, isError, isFetching } = useQuery({
    queryKey: qk.recipes(queryParams),
    queryFn: () => doctorApi.browseRecipes(queryParams),
    placeholderData: (prev) => prev,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Recipes</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {isLoading ? 'Loading…' : `${recipes.length} recipes`}
            {isFetching && !isLoading && (
              <Loader2 size={12} className="inline-block animate-spin ml-2 text-[#1E7C45]" />
            )}
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
        >
          <Plus size={15} />
          Add Recipe
        </button>
      </div>

      {/* ── Add recipe form ────────────────────────────────────────── */}
            {showAddForm && (
        <AddRecipeForm
          onSuccess={() => setShowAddForm(false)}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {/* ── Filters ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 mb-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
            <input
              type="text"
              value={search}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Search recipes…"
              className="w-52 h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-0 border border-[#D1D5DB] rounded-md overflow-hidden">
            {MEAL_TIMES.map(mt => (
              <button
                key={mt}
                onClick={() => setMealTimeFilter(mt)}
                className={`h-9 px-3 text-xs font-medium transition-colors ${
                  mealTimeFilter === mt ? 'bg-[#1E7C45] text-white' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
                }`}
              >
                {mt}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-0 border border-[#D1D5DB] rounded-md overflow-hidden">
            {VERIFIED_OPTIONS.map(v => (
              <button
                key={v}
                onClick={() => setVerifiedFilter(v)}
                className={`h-9 px-3 text-xs font-medium transition-colors ${
                  verifiedFilter === v ? 'bg-[#1E7C45] text-white' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Recipe grid ──────────────────────────────────────────── */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={28} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : isError ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 text-center">
          <AlertCircle size={32} className="text-[#DC2626] mx-auto mb-3" />
          <p className="text-base font-medium text-[#374151]">Could not load recipes</p>
        </div>
      ) : recipes.length === 0 ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 text-center">
          <ChefHat size={36} className="text-[#D1D5DB] mx-auto mb-3" />
          <p className="text-base font-medium text-[#374151]">No recipes found</p>
          <p className="text-sm text-[#6B7280] mt-1">Try adjusting your search or add a new recipe</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {recipes.map((recipe: FoodItemSummary) => (
            <RecipeCard key={recipe.id} recipe={recipe} onAssign={setAssignRecipe} />
          ))}
        </div>
      )}

      {/* Assign Recipe Modal */}
      {assignRecipe && (
        <AssignModal
          recipe={assignRecipe}
          onClose={() => setAssignRecipe(null)}
        />
      )}
    </div>
  );
}
