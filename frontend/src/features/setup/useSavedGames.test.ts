import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { deleteGame, getExistingGames } from '../../api/games';
import type { GameSave } from '../../misc/types';
import { useSavedGames } from './useSavedGames';

vi.mock('../../api/games', () => ({
  deleteGame: vi.fn(),
  getExistingGames: vi.fn(),
}));

const mockedDeleteGame = vi.mocked(deleteGame);
const mockedGetExistingGames = vi.mocked(getExistingGames);

const save: GameSave = {
  playerName: 'Mira',
  playerDescription: 'Veteran',
  worldTheme: 'Undersea ruins',
  gameOverSummary: '',
  gameOver: false,
  createdAt: '2026-06-01T10:00:00.000000',
  updatedAt: '2026-06-02T11:30:00.000000',
  objectIDString: 'save-1',
  chatHistory: [],
};

describe('useSavedGames', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads saves when the setup modal opens', async () => {
    mockedGetExistingGames.mockResolvedValue([save]);

    const { result } = renderHook(() => useSavedGames(true));

    await waitFor(() => {
      expect(result.current.isLoadingSaves).toBe(false);
      expect(result.current.existingGames).toEqual([save]);
    });
  });

  it('deletes saves and clears the selected save', async () => {
    mockedGetExistingGames.mockResolvedValue([save]);
    mockedDeleteGame.mockResolvedValue({ ok: true, status: 200, data: {} });

    const { result } = renderHook(() => useSavedGames(true));

    await waitFor(() => {
      expect(result.current.existingGames).toEqual([save]);
    });

    act(() => {
      result.current.setSelectedSave(save);
    });

    await act(async () => {
      await result.current.deleteGame(save);
    });

    expect(mockedDeleteGame).toHaveBeenCalledWith('save-1');
    expect(result.current.selectedSave).toBeNull();
    expect(result.current.existingGames).toEqual([]);
  });
});
