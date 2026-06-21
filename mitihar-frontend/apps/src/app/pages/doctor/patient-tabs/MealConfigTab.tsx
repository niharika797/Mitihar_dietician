import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, X, Search, CheckCircle, RotateCcw } from 'lucide-react';
import { doctorApi, DishPreference, FoodItemSummary } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';

interface MealConfigTabProps {
  patientId: number;
}

function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// ── Dish search + pin/block section ─────────────────────────────────────────

interface DishSectionProps {
  patientId: number;
  type: 'pin' | 'block';
  title: string;
  subtext: string;
  dishes: DishPreference[];
  emptyMsg: string;
  onChanged: () => void;
}

function DishSection({ patientId, type, title, subtext, dishes, emptyMsg, onChanged }: DishSectionProps) {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const { data: results = [] } = useQuery({
    queryKey: qk.recipes({ search: debouncedSearch, _section: type }),
    queryFn: () => doctorApi.browseRecipes({ search: debouncedSearch }),
    enabled: debouncedSearch.length > 1,
  });

  const addMutation = useMutation({
    mutationFn: (food_id: number) =>
      type === 'pin' ? doctorApi.pinDish(patientId, food_id) : doctorApi.blockDish(patientId, food_id),
    onSuccess: () => {
      onChanged();
      setSearch('');
      setDropdownOpen(false);
      toast.success(type === 'pin' ? 'Dish pinned' : 'Dish blocked');
    },
    onError: () => toast.error('Failed to update preference'),
  });

  const removeMutation = useMutation({
    mutationFn: (food_id: number) =>
      type === 'pin' ? doctorApi.unpinDish(patientId, food_id) : doctorApi.unblockDish(patientId, food_id),
    onSuccess: () => {
      onChanged();
      toast.success(type === 'pin' ? 'Dish unpinned' : 'Dish unblocked');
    },
    onError: () => toast.error('Failed to remove preference'),
  });

  const visible = results.slice(0, 10);

  return (
    <div>
      <h2 className="text-lg font-semibold text-[#111827]">{title}</h2>
      <p className="text-sm text-[#6B7280] mt-0.5 mb-4">{subtext}</p>

      <div className="bg-white border border-[#E5E7EB] rounded-lg mb-3">
        {dishes.length === 0 ? (
          <p className="text-sm text-[#9CA3AF] py-5 text-center">{emptyMsg}</p>
        ) : (
          <ul className="divide-y divide-[#F3F4F6]">
            {dishes.map(d => (
              <li key={d.food_id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-[#111827]">{d.recipe_name}</p>
                  <p className="text-xs text-[#6B7280]">{d.calories_per_serving} kcal/serving</p>
                </div>
                <button
                  onClick={() => removeMutation.mutate(d.food_id)}
                  disabled={removeMutation.isPending}
                  className="p-1 text-[#9CA3AF] hover:text-red-500 transition-colors rounded"
                >
                  <X size={15} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="relative">
        <div className="flex items-center gap-2 border border-[#D1D5DB] rounded-md px-3 bg-white">
          <Search size={14} className="text-[#9CA3AF] flex-shrink-0" />
          <input
            type="text"
            value={search}
            onChange={e => { setSearch(e.target.value); setDropdownOpen(true); }}
            onFocus={() => search.length > 1 && setDropdownOpen(true)}
            onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
            placeholder={`Search and ${type} a dish…`}
            className="flex-1 h-9 text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none bg-transparent"
          />
        </div>

        {dropdownOpen && debouncedSearch.length > 1 && visible.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#E5E7EB] rounded-lg shadow-md z-10 max-h-48 overflow-y-auto">
            {visible.map((r: FoodItemSummary) => (
              <button
                key={r.id}
                onMouseDown={() => addMutation.mutate(r.id)}
                disabled={addMutation.isPending}
                className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-[#F0FDF4] transition-colors disabled:opacity-50"
              >
                <div>
                  <p className="text-sm text-[#111827]">{r.recipe_name}</p>
                  <p className="text-xs text-[#6B7280]">{r.cal_per_serving} kcal · {r.slot_type}</p>
                </div>
                {r.is_verified && (
                  <CheckCircle size={13} className="text-[#1E7C45] flex-shrink-0 ml-2" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main tab ─────────────────────────────────────────────────────────────────

export function MealConfigTab({ patientId }: MealConfigTabProps) {
  const queryClient = useQueryClient();

  const [bfPct, setBfPct] = useState(25);
  const [luPct, setLuPct] = useState(35);
  const [diPct, setDiPct] = useState(25);

  const total = bfPct + luPct + diPct;
  const isValid = total === 85;

  const { data: config, isLoading } = useQuery({
    queryKey: qk.patientMealConfig(patientId),
    queryFn: () => doctorApi.getMealConfig(patientId),
  });

  useEffect(() => {
    if (config?.meal_split) {
      setBfPct(config.meal_split.Breakfast);
      setLuPct(config.meal_split.Lunch);
      setDiPct(config.meal_split.Dinner);
    }
  }, [config?.meal_split?.Breakfast, config?.meal_split?.Lunch, config?.meal_split?.Dinner]);

  const saveMutation = useMutation({
    mutationFn: (split: { Breakfast: number; Lunch: number; Dinner: number } | null) =>
      doctorApi.patchMealConfig(patientId, { meal_split: split, regenerate_plan: true }),
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: qk.patientMealConfig(patientId) });
      toast.success('Config saved. Plan regenerating…');
      if (!result.plan_regenerated && result.error) {
        toast.error(`Regen failed: ${result.error}`);
      }
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: qk.patientPlan(patientId) });
      }, 2000);
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to save config');
    },
  });

  const invalidateMealConfig = () =>
    queryClient.invalidateQueries({ queryKey: qk.patientMealConfig(patientId) });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-8">
      {/* Section 1: TDEE Split */}
      <div>
        <h2 className="text-lg font-semibold text-[#111827]">Calorie Distribution</h2>
        <p className="text-sm text-[#6B7280] mt-0.5 mb-4">
          Adjusts how daily calories are split. Total must equal 85% — the remaining 15% is the passive buffer.
        </p>

        <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-[#374151] mb-1">Breakfast %</label>
              <input
                type="number"
                min={1}
                max={83}
                value={bfPct}
                onChange={e => setBfPct(Math.max(1, Math.min(83, Number(e.target.value) || 1)))}
                className="w-full h-9 px-3 border border-[#D1D5DB] rounded-md text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#374151] mb-1">Lunch %</label>
              <input
                type="number"
                min={1}
                max={83}
                value={luPct}
                onChange={e => setLuPct(Math.max(1, Math.min(83, Number(e.target.value) || 1)))}
                className="w-full h-9 px-3 border border-[#D1D5DB] rounded-md text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#374151] mb-1">Dinner %</label>
              <input
                type="number"
                min={1}
                max={83}
                value={diPct}
                onChange={e => setDiPct(Math.max(1, Math.min(83, Number(e.target.value) || 1)))}
                className="w-full h-9 px-3 border border-[#D1D5DB] rounded-md text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
              />
            </div>
          </div>

          <p className={`text-sm font-medium ${isValid ? 'text-[#15803d]' : 'text-red-600'}`}>
            Total: {total}% + 15% buffer = 100%
            {isValid ? ' ✓ Valid' : ' — Must equal 85%'}
          </p>

          <div className="flex items-center gap-4">
            <button
              onClick={() => saveMutation.mutate({ Breakfast: bfPct, Lunch: luPct, Dinner: diPct })}
              disabled={!isValid || saveMutation.isPending}
              className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
            >
              {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
              Save &amp; Regenerate Plan
            </button>
            <button
              onClick={() => saveMutation.mutate(null)}
              disabled={saveMutation.isPending}
              className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#374151] transition-colors disabled:opacity-40"
            >
              <RotateCcw size={13} />
              Reset to Default
            </button>
          </div>
        </div>
      </div>

      {/* Section 2: Pinned Dishes */}
      <DishSection
        patientId={patientId}
        type="pin"
        title="Always Include"
        subtext="These dishes will be prioritized in this patient's next generated plan."
        dishes={config?.pinned_dishes ?? []}
        emptyMsg="No pinned dishes yet."
        onChanged={invalidateMealConfig}
      />

      {/* Section 3: Blocked Dishes */}
      <DishSection
        patientId={patientId}
        type="block"
        title="Never Show"
        subtext="These dishes will never appear in this patient's generated plan."
        dishes={config?.blocked_dishes ?? []}
        emptyMsg="No blocked dishes yet."
        onChanged={invalidateMealConfig}
      />
    </div>
  );
}
