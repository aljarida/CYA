import { beforeEach, describe, expect, it, vi } from 'vitest';

import { API_INITIALIZE_URL } from '../misc/enums';
import { getExistingGames, initializeGame } from './games';

describe('games API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sorts saves and normalizes assistant chat history roles', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: vi.fn().mockResolvedValue({
        results: [
          {
            playerName: 'Old',
            playerDescription: 'A',
            worldTheme: 'Forest',
            gameOverSummary: '',
            gameOver: false,
            createdAt: '2026-01-01T00:00:00.000000',
            updatedAt: '2026-01-01T00:00:00.000000',
            objectIDString: 'old',
            chatHistory: [{ role: 'assistant', content: 'Old narration' }],
          },
          {
            playerName: 'New',
            playerDescription: 'B',
            worldTheme: 'Moon',
            gameOverSummary: '',
            gameOver: false,
            createdAt: '2026-01-02T00:00:00.000000',
            updatedAt: '2026-01-03T00:00:00.000000',
            objectIDString: 'new',
            chatHistory: [{ role: 'user', content: 'Look around' }],
          },
        ],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const saves = await getExistingGames();

    expect(saves.map((save) => save.objectIDString)).toEqual(['new', 'old']);
    expect(saves[1].chatHistory[0]).toEqual({
      role: 'gamemaster',
      content: 'Old narration',
    });
  });

  it('normalizes assistant senders in initialize responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({
        sender: 'assistant',
        content: 'The adventure begins.',
        hitPoints: 10,
        portraitSrc: '/portrait.png',
        worldBackdropSrc: '/world.png',
        gameId: 'game-1',
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await initializeGame({
      playerName: 'Mira',
      worldTheme: 'Sky islands',
      playerDescription: 'A careful cartographer',
    });

    expect(fetchMock).toHaveBeenCalledWith(API_INITIALIZE_URL, expect.objectContaining({
      method: 'POST',
    }));
    expect(result.data.sender).toBe('gamemaster');
  });
});
