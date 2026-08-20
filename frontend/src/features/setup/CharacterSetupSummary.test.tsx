import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import CharacterSetupSummary from './CharacterSetupSummary';
import type { DraftStartingState } from './setupTypes';

const draftState: DraftStartingState = {
  startingLocation: 'a quiet harbor',
  startingInventory: [
    { name: 'hammer', description: 'a worn blacksmith hammer', weightKg: 2, quantity: 1 },
  ],
  startingConditions: [],
  attributes: { ageYears: 30, heightCm: 175, bodyWeightKg: 70, maxCarryWeightKg: 25 },
};

describe('CharacterSetupSummary', () => {
  it('renders the generated starting location, attributes, and items', () => {
    render(
      <CharacterSetupSummary
        draftState={draftState}
        onChange={vi.fn()}
        onRegenerate={vi.fn()}
        onConfirm={vi.fn()}
        isRegenerating={false}
      />,
    );

    expect(screen.getByDisplayValue('a quiet harbor')).toBeTruthy();
    expect(screen.getByDisplayValue('hammer')).toBeTruthy();
    expect(screen.getByDisplayValue('30')).toBeTruthy();
  });

  it('calls onChange with an added blank item when Add item is clicked', async () => {
    const onChange = vi.fn();
    render(
      <CharacterSetupSummary
        draftState={draftState}
        onChange={onChange}
        onRegenerate={vi.fn()}
        onConfirm={vi.fn()}
        isRegenerating={false}
      />,
    );

    await userEvent.click(screen.getByText('+ Add item'));

    expect(onChange).toHaveBeenCalledWith({
      ...draftState,
      startingInventory: [...draftState.startingInventory, { name: '', description: '', weightKg: 0, quantity: 1 }],
    });
  });

  it('calls onChange without the item when its remove button is clicked', async () => {
    const onChange = vi.fn();
    render(
      <CharacterSetupSummary
        draftState={draftState}
        onChange={onChange}
        onRegenerate={vi.fn()}
        onConfirm={vi.fn()}
        isRegenerating={false}
      />,
    );

    await userEvent.click(screen.getByTitle('Remove item'));

    expect(onChange).toHaveBeenCalledWith({ ...draftState, startingInventory: [] });
  });

  it('calls onRegenerate and shows a disabled state while regenerating', async () => {
    const onRegenerate = vi.fn();
    render(
      <CharacterSetupSummary
        draftState={draftState}
        onChange={vi.fn()}
        onRegenerate={onRegenerate}
        onConfirm={vi.fn()}
        isRegenerating={true}
      />,
    );

    const regenerateButton = screen.getByText('Regenerating…');
    expect(regenerateButton).toBeTruthy();
    expect((regenerateButton as HTMLButtonElement).disabled).toBe(true);
  });

  it('calls onConfirm when Confirm & Start is clicked', async () => {
    const onConfirm = vi.fn();
    render(
      <CharacterSetupSummary
        draftState={draftState}
        onChange={vi.fn()}
        onRegenerate={vi.fn()}
        onConfirm={onConfirm}
        isRegenerating={false}
      />,
    );

    await userEvent.click(screen.getByText(/confirm & start/i));

    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
