import type { ChangeEvent } from 'react';
import { Trash2 } from 'lucide-react';

import type { DraftInventoryItem, DraftStartingState } from './setupTypes';

type CharacterSetupSummaryProps = {
  draftState: DraftStartingState;
  onChange: (next: DraftStartingState) => void;
  onRegenerate: () => void;
  onConfirm: () => void;
  isRegenerating: boolean;
};

const fieldBaseClass =
  'p-2 bg-neutral-800/80 backdrop-blur-sm text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 border border-neutral-700/50 text-sm placeholder-neutral-500';
const inputClass = `w-full ${fieldBaseClass}`;

function CharacterSetupSummary({ draftState, onChange, onRegenerate, onConfirm, isRegenerating }: CharacterSetupSummaryProps) {
  const updateAttribute = (field: keyof DraftStartingState['attributes'], value: number) => {
    onChange({ ...draftState, attributes: { ...draftState.attributes, [field]: value } });
  };

  const updateItem = <K extends keyof DraftInventoryItem>(index: number, field: K, value: DraftInventoryItem[K]) => {
    const items = draftState.startingInventory.map((item, i) => (i === index ? { ...item, [field]: value } : item));
    onChange({ ...draftState, startingInventory: items });
  };

  const removeItem = (index: number) => {
    onChange({ ...draftState, startingInventory: draftState.startingInventory.filter((_, i) => i !== index) });
  };

  const addItem = () => {
    onChange({
      ...draftState,
      startingInventory: [...draftState.startingInventory, { name: '', description: '', weightKg: 0, quantity: 1 }],
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-200 py-3 mb-1">Character Summary</h2>
        <p className="text-neutral-400 text-sm">Review and edit your starting state before beginning.</p>
      </div>

      <div>
        <label className="block text-neutral-300 mb-1.5">Starting Location</label>
        <input
          className={inputClass}
          value={draftState.startingLocation}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange({ ...draftState, startingLocation: e.target.value })}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-neutral-300 mb-1.5 text-sm">Age</label>
          <input
            type="number"
            className={inputClass}
            value={draftState.attributes.ageYears}
            onChange={(e) => updateAttribute('ageYears', Number(e.target.value))}
          />
        </div>
        <div>
          <label className="block text-neutral-300 mb-1.5 text-sm">Height (cm)</label>
          <input
            type="number"
            className={inputClass}
            value={draftState.attributes.heightCm}
            onChange={(e) => updateAttribute('heightCm', Number(e.target.value))}
          />
        </div>
        <div>
          <label className="block text-neutral-300 mb-1.5 text-sm">Body Weight (kg)</label>
          <input
            type="number"
            className={inputClass}
            value={draftState.attributes.bodyWeightKg}
            onChange={(e) => updateAttribute('bodyWeightKg', Number(e.target.value))}
          />
        </div>
        <div>
          <label className="block text-neutral-300 mb-1.5 text-sm">Max Carry Weight (kg)</label>
          <input
            type="number"
            className={inputClass}
            value={draftState.attributes.maxCarryWeightKg}
            onChange={(e) => updateAttribute('maxCarryWeightKg', Number(e.target.value))}
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-neutral-300">Starting Inventory</label>
          <button type="button" onClick={addItem} className="text-xs text-neutral-400 hover:text-neutral-200">
            + Add item
          </button>
        </div>
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          {draftState.startingInventory.map((item, index) => (
            <div key={index} className="space-y-1.5 bg-neutral-800/50 p-2 rounded-lg">
              <div className="flex items-center gap-2">
                <input
                  className={`${fieldBaseClass} flex-1 min-w-0`}
                  placeholder="Item name"
                  value={item.name}
                  onChange={(e) => updateItem(index, 'name', e.target.value)}
                />
                <input
                  type="number"
                  className={`${fieldBaseClass} w-14`}
                  placeholder="qty"
                  min={1}
                  value={item.quantity}
                  onChange={(e) => updateItem(index, 'quantity', Math.max(1, Number(e.target.value)))}
                />
                <input
                  type="number"
                  className={`${fieldBaseClass} w-20`}
                  placeholder="kg"
                  min={0}
                  value={item.weightKg}
                  onChange={(e) => updateItem(index, 'weightKg', Math.max(0, Number(e.target.value)))}
                />
                <button
                  type="button"
                  onClick={() => removeItem(index)}
                  className="p-1.5 text-neutral-500 hover:text-red-400 transition-colors"
                  title="Remove item"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <input
                className={inputClass}
                placeholder="Description (optional)"
                value={item.description}
                onChange={(e) => updateItem(index, 'description', e.target.value)}
              />
            </div>
          ))}
          {draftState.startingInventory.length === 0 && (
            <p className="text-neutral-500 text-sm italic">No starting items.</p>
          )}
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onRegenerate}
          disabled={isRegenerating}
          className="flex-1 py-3 rounded-lg border border-neutral-600/50 text-neutral-300 hover:bg-neutral-800/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRegenerating ? 'Regenerating…' : 'Regenerate'}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="flex-1 py-3 rounded-lg bg-green-700/70 hover:bg-green-600/70 text-neutral-200 border border-neutral-600/50 shadow-lg transition-colors"
        >
          Confirm &amp; Start
        </button>
      </div>
    </div>
  );
}

export default CharacterSetupSummary;
