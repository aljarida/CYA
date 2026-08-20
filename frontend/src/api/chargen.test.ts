import { describe, expect, it, vi } from 'vitest';

import { API_GENERATE_STARTING_STATE_URL } from '../misc/enums';
import { generateStartingState } from './chargen';

describe('chargen API', () => {
  it('posts game info and returns the draft starting state unchanged', async () => {
    const draft = {
      startingLocation: 'a quiet harbor',
      startingInventory: [{ name: 'hammer', description: '', weightKg: 2, quantity: 1 }],
      startingConditions: [],
      attributes: { ageYears: 30, heightCm: 175, bodyWeightKg: 70, maxCarryWeightKg: 25 },
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(draft),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await generateStartingState({
      playerName: 'Aldric',
      worldTheme: 'a besieged village',
      playerDescription: 'a weary blacksmith',
    });

    expect(fetchMock).toHaveBeenCalledWith(
      API_GENERATE_STARTING_STATE_URL,
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result.data).toEqual(draft);
  });
});
