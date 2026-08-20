import { describe, expect, it, vi } from 'vitest';

import { API_DISCARD_ITEM_URL } from '../misc/enums';
import { discardItem } from './inventory';

describe('inventory API', () => {
  it('posts gameId and itemId and normalizes the assistant sender', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({
        sender: 'system',
        content: 'You discard the brass key.',
        worldState: { inventory: [] },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await discardItem('game-1', 'item-1');

    expect(fetchMock).toHaveBeenCalledWith(
      API_DISCARD_ITEM_URL,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ gameId: 'game-1', itemId: 'item-1' }),
      }),
    );
    expect(result.data.content).toBe('You discard the brass key.');
    expect(result.data.sender).toBe('system');
  });
});
