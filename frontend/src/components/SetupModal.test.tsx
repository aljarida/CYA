import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SetupModal from './SetupModal';
import { useSavedGames } from '../features/setup/useSavedGames';
import type { DraftStartingState } from '../features/setup/setupTypes';

vi.mock('../features/setup/useSavedGames', () => ({
  useSavedGames: vi.fn(),
}));

const mockedUseSavedGames = vi.mocked(useSavedGames);

const gameInfo = {
  playerName: 'Aldric',
  worldTheme: 'A besieged village',
  playerDescription: 'A weary blacksmith',
};

const draftState: DraftStartingState = {
  startingLocation: 'a quiet harbor',
  startingInventory: [],
  startingConditions: [],
  attributes: { ageYears: 30, heightCm: 175, bodyWeightKg: 70, maxCarryWeightKg: 25 },
};

function renderSetupModal(overrides = {}) {
  const props = {
    showModal: true,
    formSubmitted: false,
    gameInfo,
    isFormValid: true,
    handleInputChange: vi.fn(),
    onSubmit: vi.fn().mockResolvedValue(undefined),
    setIsFormValid: vi.fn(),
    setupStep: 'form' as const,
    draftState: null,
    onDraftChange: vi.fn(),
    onRegenerateDraft: vi.fn(),
    isRegeneratingDraft: false,
    onConfirmDraft: vi.fn(),
    ...overrides,
  };

  render(<SetupModal {...props} />);
  return props;
}

describe('SetupModal', () => {
  beforeEach(() => {
    mockedUseSavedGames.mockReturnValue({
      existingGames: [],
      isLoadingSaves: false,
      selectedSave: null,
      setSelectedSave: vi.fn(),
      deleteGame: vi.fn(),
    });
  });

  it('shows the setup form on the form step', () => {
    renderSetupModal();

    expect(screen.getByRole('button', { name: /begin adventure/i })).toBeTruthy();
  });

  it('shows a loading state while a request is in flight', () => {
    renderSetupModal({ formSubmitted: true });

    expect(screen.queryByRole('button', { name: /begin adventure/i })).toBeNull();
  });

  it('shows the character summary once a draft is generated', () => {
    renderSetupModal({ setupStep: 'summary', draftState });

    expect(screen.getByText('Character Summary')).toBeTruthy();
    expect(screen.getByDisplayValue('a quiet harbor')).toBeTruthy();
  });

  it('calls onConfirmDraft when Confirm & Start is clicked on the summary step', async () => {
    const props = renderSetupModal({ setupStep: 'summary', draftState });

    await userEvent.click(screen.getByText(/confirm & start/i));

    expect(props.onConfirmDraft).toHaveBeenCalledOnce();
  });
});
