import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Plus, Search, ChefHat, Flame, Beef, Wheat, Sparkles,
  Loader2, X, AlertCircle,
} from 'lucide-react';
import apiClient from '../../../lib/axios';
import { doctorApi, FoodItemSummary } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';

const MEAL_TIMES = ['All', 'Breakfast', 'MorningSnacks', 'Lunch', 'EveningSnacks', 'Dinner'];

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
  diet_type: 'Vegetarian',
  meal_time: 'Breakfast',
  region: '',
};

export function Recipes() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [mealTimeFilter, setMealTimeFilter] = useState('All');
  const [showAddForm, setShowAddForm] = useState(false);
  const [form, setForm] = useState<AddForm>(EMPTY_FORM);

  // AI estimation state
  const [nameInput, setNameInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiEstimate, setAiEstimate] = useState<AiEstimate | null>(null);
  const [aiError, setAiError] = useState('');
  const [aiHighlighted, setAiHighlighted] = useState(false);

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
  };

  const { data: recipes = [], isLoading, isError, isFetching } = useQuery({
    queryKey: qk.recipes(queryParams),
    queryFn: () => doctorApi.browseRecipes(queryParams),
    placeholderData: (prev) => prev,
  });

  // Add recipe mutation
  const addMutation = useMutation({
    mutationFn: () =>
      doctorApi.addRecipe({
        recipe_name: form.recipe_name,
        slot_type: form.slot_type,
        cal_per_serving: Number(form.calories),
        protein_per_serving: Number(form.protein),
        carbs_per_serving: Number(form.carbs),
        fat_per_serving: Number(form.fat),
        fiber_per_serving: Number(form.fiber) || 0,
        diet_type: form.diet_type,
        meal_time_tags: form.meal_time ? [form.meal_time] : [],
        plan_type_tags: ['Healthy'],
        ingredients: [],
        region_tags: form.region ? [form.region] : [],
      }),
    onSuccess: () => {
      // Invalidate all recipe queries so the list refreshes
      queryClient.invalidateQueries({ queryKey: ['doctor', 'recipes'] });
      setShowAddForm(false);
      setForm(EMPTY_FORM);
      setNameInput('');
      setAiEstimate(null);
      setAiHighlighted(false);
      toast.success('Recipe added — pending admin approval');
    },
    onError: () => toast.error('Failed to add recipe'),
  });

  const handleNameChange = (val: string) => {
    setNameInput(val);
    setForm(p => ({ ...p, recipe_name: val }));
    setAiEstimate(null);
    setAiError('');
    setAiHighlighted(false);
  };

  const handleEstimate = async () => {
    if (!nameInput.trim()) return;
    setAiLoading(true);
    setAiError('');
    setAiEstimate(null);
    try {
      const { data } = await apiClient.post<AiEstimate & { ai_estimated: boolean }>(
        '/doctor/recipes/estimate',
        { dish_name: nameInput.trim() },
      );
      setAiEstimate(data);
      setAiHighlighted(true);
      setForm(p => ({
        ...p,
        recipe_name: data.dish_name || p.recipe_name,
        calories: String(data.calories),
        protein: String(data.protein),
        carbs: String(data.carbs),
        fat: String(data.fat),
      }));
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setAiError(msg ?? 'Could not estimate nutrition. Please fill in values manually.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleAddRecipe = (e: React.FormEvent) => {
    e.preventDefault();
    addMutation.mutate();
  };

  const macroInputClass = (highlighted: boolean) =>
    `w-full h-10 px-3 rounded-md border text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent transition-colors ${
      highlighted ? 'border-[#F59E0B] bg-[#FFFBEB]' : 'border-[#D1D5DB] bg-white'
    }`;

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
          onClick={() => {
            setShowAddForm(!showAddForm);
            setAiEstimate(null);
            setAiError('');
            setNameInput('');
          }}
          className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
        >
          <Plus size={15} />
          Add Recipe
        </button>
      </div>

      {/* ── Add recipe form ────────────────────────────────────────── */}
      {showAddForm && (
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 mb-6">
          <h2 className="text-base font-medium text-[#111827] mb-4">Add Recipe to Library</h2>
          <form onSubmit={handleAddRecipe} className="max-w-xl">
            <div className="grid grid-cols-2 gap-4 mb-4">

              {/* Recipe name + AI estimate */}
              <div className="col-span-2">
                <label className="block text-sm font-medium text-[#374151] mb-1.5">
                  Recipe Name <span className="text-[#DC2626] ml-0.5">*</span>
                </label>
                <input
                  required
                  value={nameInput}
                  onChange={e => handleNameChange(e.target.value)}
                  placeholder="e.g. Moong Dal Cheela"
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
                />

                {nameInput.trim().length >= 2 && !aiEstimate && (
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleEstimate}
                      disabled={aiLoading}
                      className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#D1D5DB] text-xs font-medium text-[#374151] hover:bg-[#F9FAFB] transition-colors disabled:opacity-50"
                    >
                      {aiLoading
                        ? <><Loader2 size={12} className="animate-spin" /> Estimating…</>
                        : <><Sparkles size={12} className="text-[#F59E0B]" /> Estimate with AI</>
                      }
                    </button>
                    {aiError && <p className="text-xs text-[#DC2626]">{aiError}</p>}
                  </div>
                )}

                {aiEstimate && (
                  <div className="mt-2 flex items-start gap-2 px-3 py-2 bg-[#FFFBEB] border border-[#FDE68A] rounded-md">
                    <Sparkles size={13} className="text-[#F59E0B] mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-[#92400E]">
                        AI estimate applied — please verify before saving
                      </p>
                      {aiEstimate.serving_description && (
                        <p className="text-xs text-[#B45309] mt-0.5">
                          Serving: {aiEstimate.serving_description}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => { setAiEstimate(null); setAiHighlighted(false); }}
                      className="text-[#9CA3AF] hover:text-[#374151]"
                    >
                      <X size={12} />
                    </button>
                  </div>
                )}
              </div>

              {/* Slot type */}
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Slot Type</label>
                <select
                  value={form.slot_type}
                  onChange={e => setForm(p => ({ ...p, slot_type: e.target.value }))}
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                >
                  {['grain', 'dal_protein', 'main_dish', 'sabzi', 'beverage', 'snack', 'fruit', 'egg_dish'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Diet type */}
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Diet Type</label>
                <select
                  value={form.diet_type}
                  onChange={e => setForm(p => ({ ...p, diet_type: e.target.value }))}
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                >
                  {['Vegetarian', 'Non-Vegetarian', 'Eggetarian'].map(d => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </div>

              {/* Meal time */}
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Meal Time</label>
                <select
                  value={form.meal_time}
                  onChange={e => setForm(p => ({ ...p, meal_time: e.target.value }))}
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                >
                  {['Breakfast', 'MorningSnacks', 'Lunch', 'EveningSnacks', 'Dinner'].map(t => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Region */}
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Region</label>
                <input
                  value={form.region}
                  onChange={e => setForm(p => ({ ...p, region: e.target.value }))}
                  placeholder="e.g. South Indian"
                  className="w-full h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                />
              </div>

              {/* Macro fields */}
              {([
                { key: 'calories' as const, label: 'Calories (kcal) *' },
                { key: 'protein'  as const, label: 'Protein (g) *'     },
                { key: 'carbs'    as const, label: 'Carbs (g) *'       },
                { key: 'fat'      as const, label: 'Fat (g) *'         },
                { key: 'fiber'    as const, label: 'Fiber (g)'         },
              ]).map(f => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-[#374151] mb-1.5">{f.label}</label>
                  <input
                    required={f.key !== 'fiber'}
                    type="number"
                    min={0}
                    value={form[f.key]}
                    onChange={e => {
                      setForm(p => ({ ...p, [f.key]: e.target.value }));
                      setAiHighlighted(false);
                    }}
                    placeholder="0"
                    className={macroInputClass(aiHighlighted && ['calories','protein','carbs','fat'].includes(f.key))}
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={addMutation.isPending}
                className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {addMutation.isPending && <Loader2 size={13} className="animate-spin" />}
                Add to Recipe Library
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddForm(false);
                  setNameInput('');
                  setAiEstimate(null);
                  setAiHighlighted(false);
                  setForm(EMPTY_FORM);
                }}
                className="h-9 px-4 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB] transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Filters ──────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
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
              {mt === 'MorningSnacks' ? 'AM Snack' : mt === 'EveningSnacks' ? 'PM Snack' : mt}
            </button>
          ))}
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
            <div
              key={recipe.id}
              className="bg-white border border-[#E5E7EB] rounded-lg p-4 hover:border-[#D1D5DB] transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <span className="text-xs text-[#6B7280]">
                    {recipe.slot_type} · {recipe.diet_type}
                  </span>
                  <p className="text-sm font-medium text-[#111827] mt-0.5">{recipe.recipe_name}</p>
                </div>
                {!recipe.is_verified && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] flex-shrink-0">
                    Pending
                  </span>
                )}
              </div>

              {recipe.meal_time_tags.length > 0 && (
                <div className="flex gap-1 mb-2 flex-wrap">
                  {recipe.meal_time_tags.map(t => (
                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-[#F3F4F6] text-[#6B7280]">
                      {t}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-3 mt-3 flex-wrap">
                <span className="flex items-center gap-1 text-xs text-[#DC2626]">
                  <Flame size={11} />
                  <span className="tabular-nums font-medium">{Math.round(recipe.cal_per_serving)}</span> kcal
                </span>
                <span className="flex items-center gap-1 text-xs text-[#2563EB]">
                  <Beef size={11} />
                  <span className="tabular-nums font-medium">{recipe.protein_per_serving.toFixed(1)}g</span> P
                </span>
                <span className="flex items-center gap-1 text-xs text-[#F59E0B]">
                  <Wheat size={11} />
                  <span className="tabular-nums font-medium">{recipe.carbs_per_serving.toFixed(1)}g</span> C
                </span>
              </div>

              <p className="text-xs text-[#9CA3AF] mt-3">
                Source: {recipe.source}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
