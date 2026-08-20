import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { GameSave } from '../misc/types';
import SetupForm from './SetupForm';

const gameInfo = {
  playerName: 'Mira',
  worldTheme: 'Sky islands',
  playerDescription: 'A careful cartographer',
};

const save: GameSave = {
  playerName: 'Saved Hero',
  playerDescription: 'Veteran',
  worldTheme: 'Undersea ruins',
  gameOverSummary: '',
  gameOver: false,
  createdAt: '2026-06-01T10:00:00.000000',
  updatedAt: '2026-06-02T11:30:00.000000',
  objectIDString: 'save-1',
  chatHistory: [],
};

function renderSetupForm(overrides = {}) {
  const props = {
    gameInfo,
    isFormValid: true,
    handleInputChange: vi.fn(),
    onSubmit: vi.fn().mockResolvedValue(undefined),
    existingGames: [],
    isLoadingSaves: false,
    selectedSave: null,
    setSelectedSave: vi.fn(),
    deleteGame: vi.fn(),
    ...overrides,
  };

  render(<SetupForm {...props} />);
  return props;
}

describe('SetupForm', () => {
  it('renders new-adventure fields and submits null for a new game', async () => {
    const user = userEvent.setup();
    const props = renderSetupForm();

    expect(screen.getByLabelText(/player name/i)).toHaveValue('Mira');
    expect(screen.getByLabelText(/game theme/i)).toHaveValue('Sky islands');
    expect(screen.getByLabelText(/description of player character/i)).toHaveValue('A careful cartographer');

    await user.click(screen.getByRole('button', { name: /begin adventure/i }));

    expect(props.onSubmit).toHaveBeenCalledWith(null);
  });

  it('disables new game submission when the form is invalid', () => {
    renderSetupForm({
      isFormValid: false,
      gameInfo: {
        playerName: 'Foo',
        worldTheme: '',
        playerDescription: '',
      },
    });

    expect(screen.getByRole('button', { name: /begin adventure/i })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent(/please fill out all fields/i);
  });

  it('selects an existing save and shows save actions', async () => {
    const user = userEvent.setup();
    const props = renderSetupForm({ existingGames: [save] });

    await user.selectOptions(screen.getByRole('combobox'), 'save-1');

    expect(props.setSelectedSave).toHaveBeenCalledWith(save);
  });

  it('requires a second click before deleting a selected save', async () => {
    const user = userEvent.setup();
    const props = renderSetupForm({ existingGames: [save], selectedSave: save });

    await user.click(screen.getByRole('button', { name: /delete adventure/i }));

    expect(props.deleteGame).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /confirm deletion/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /confirm deletion/i }));

    expect(props.deleteGame).toHaveBeenCalledWith(save);
  });
});
