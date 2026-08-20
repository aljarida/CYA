import { beforeEach, describe, expect, it, vi } from 'vitest';

import getJsonRequest from './getjsonrequest';
import postJsonRequest from './postjsonrequest';

describe('JSON request helpers', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('builds query strings and returns parsed GET responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({ results: ['save-1'] }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await getJsonRequest('/api/existing_games', { gameId: 'abc 123', n: 3 });

    expect(fetchMock).toHaveBeenCalledWith('/api/existing_games?gameId=abc+123&n=3', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    expect(result).toEqual({
      ok: true,
      status: 200,
      data: { results: ['save-1'] },
    });
  });

  it('serializes POST bodies and returns response status details', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: vi.fn().mockResolvedValue({ content: 'Invalid setup' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await postJsonRequest('/api/initialize', { playerName: 'Ada' });

    expect(fetchMock).toHaveBeenCalledWith('/api/initialize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ playerName: 'Ada' }),
    });
    expect(result).toEqual({
      ok: false,
      status: 422,
      data: { content: 'Invalid setup' },
    });
  });
});
