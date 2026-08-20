import { describe, expect, it, vi } from 'vitest';

import { API_MOMENTS_URL } from '../misc/enums';
import { getMoments } from './moments';

describe('moments API', () => {
  it('fetches moments for a game and returns the results array', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({
        results: [
          { id: 'moment-1', caption: 'Iris drives back the tide-wraith.', imageSrc: 'data:image/png;base64,abc' },
        ],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const moments = await getMoments('game-1');

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_MOMENTS_URL}?gameId=game-1`,
      expect.objectContaining({ method: 'GET' }),
    );
    expect(moments).toEqual([
      { id: 'moment-1', caption: 'Iris drives back the tide-wraith.', imageSrc: 'data:image/png;base64,abc' },
    ]);
  });

  it('returns an empty array when the response has no results', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({}),
    });
    vi.stubGlobal('fetch', fetchMock);

    const moments = await getMoments('game-1');

    expect(moments).toEqual([]);
  });
});
