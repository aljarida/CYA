import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { discardItem as discardItemApi } from '../../api/inventory';
import { loadGame } from '../../api/games';
import { getMoments } from '../../api/moments';
import type { GameSave, Message, StoryMoment } from '../../misc/types';
import { useGameSession } from './useGameSession';

vi.mock('../../api/inventory', () => ({
  discardItem: vi.fn(),
}));

vi.mock('../../api/games', () => ({
  initializeGame: vi.fn(),
  loadGame: vi.fn(),
}));

vi.mock('../../api/chargen', () => ({
  generateStartingState: vi.fn(),
}));

vi.mock('../../api/moments', () => ({
  getMoments: vi.fn(),
}));

const mockedDiscardItem = vi.mocked(discardItemApi);
const mockedLoadGame = vi.mocked(loadGame);
const mockedGetMoments = vi.mocked(getMoments);

const fakeSave: GameSave = {
  playerName: 'Aldric',
  playerDescription: 'A weary blacksmith',
  worldTheme: 'A besieged village',
  gameOverSummary: '',
  gameOver: false,
  createdAt: '2026-01-01T00:00:00.000000',
  updatedAt: '2026-01-01T00:00:00.000000',
  objectIDString: 'save-1',
  chatHistory: [],
};

function setup() {
  const messages: Message[] = [];
  const addMessage = vi.fn((message: Message) => messages.push(message));
  const clearMessages = vi.fn();
  const hook = renderHook(() => useGameSession({ addMessage, clearMessages }));
  return { messages, addMessage, hook };
}

async function loadActiveGame(hook: ReturnType<typeof setup>['hook']) {
  mockedLoadGame.mockResolvedValue({
    ok: true,
    status: 200,
    data: {
      sender: 'system',
      content: 'Game state successfully loaded.',
      hitPoints: 5,
      portraitSrc: '',
      worldBackdropSrc: '',
      gameId: 'game-1',
      worldState: {
        currentLocation: '',
        inventory: [],
        totalInventoryWeightKg: 0,
        conditions: [],
        knownNpcs: {},
        relationships: {},
        quests: [],
        worldFlags: {},
      },
    },
  });

  await act(async () => {
    await hook.result.current.startOrLoadGame(fakeSave);
  });
  await waitFor(() => expect(hook.result.current.gameId).toBe('game-1'));
}

describe('useGameSession discardItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetMoments.mockResolvedValue([]);
  });

  it('does nothing when no game is active', async () => {
    const { hook } = setup();

    await act(async () => {
      await hook.result.current.discardItem('item-1');
    });

    expect(mockedDiscardItem).not.toHaveBeenCalled();
  });

  it('adds a system message and updates world state on success', async () => {
    const { hook, messages } = setup();
    await loadActiveGame(hook);

    mockedDiscardItem.mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        sender: 'system',
        content: 'You discard the brass key.',
        worldState: {
          currentLocation: '',
          inventory: [],
          totalInventoryWeightKg: 0,
          conditions: [],
          knownNpcs: {},
          relationships: {},
          quests: [],
          worldFlags: {},
        },
      },
    });

    await act(async () => {
      await hook.result.current.discardItem('item-1');
    });

    expect(mockedDiscardItem).toHaveBeenCalledWith('game-1', 'item-1');
    expect(messages.some((m) => m.sender === 'system' && m.content === 'You discard the brass key.')).toBe(true);
  });

  it('adds an error message on failure', async () => {
    const { hook, messages } = setup();
    await loadActiveGame(hook);

    mockedDiscardItem.mockResolvedValue({
      ok: false,
      status: 400,
      data: { sender: 'error', content: 'Item not found in inventory.' },
    });

    await act(async () => {
      await hook.result.current.discardItem('missing-item');
    });

    expect(messages.some((m) => m.sender === 'error' && m.content === 'Item not found in inventory.')).toBe(true);
  });
});

describe('useGameSession moments and story log', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetMoments.mockResolvedValue([]);
  });

  it('loads existing moments when an active game is loaded', async () => {
    const savedMoments: StoryMoment[] = [
      { id: 'moment-1', caption: 'Iris drives back the tide-wraith.', imageSrc: 'data:image/png;base64,abc' },
    ];
    mockedGetMoments.mockResolvedValue(savedMoments);
    const { hook } = setup();

    await loadActiveGame(hook);
    await waitFor(() => expect(hook.result.current.moments).toEqual(savedMoments));

    expect(mockedGetMoments).toHaveBeenCalledWith('game-1');
  });

  it('sets the active moment and appends it to the moment history when a turn response includes one', async () => {
    const { hook } = setup();
    await loadActiveGame(hook);

    const moment: StoryMoment = {
      id: 'moment-2',
      caption: 'Iris pulls the sword from the stone.',
      imageSrc: 'data:image/png;base64,def',
    };

    act(() => {
      hook.result.current.applyResponseEffects({
        sender: 'gamemaster',
        content: 'The sword slides free.',
        moment,
      });
    });

    expect(hook.result.current.activeMoment).toEqual(moment);
    expect(hook.result.current.moments).toEqual([moment]);
  });

  it('clears the active moment on dismiss without clearing the moment history', async () => {
    const { hook } = setup();
    await loadActiveGame(hook);

    const moment: StoryMoment = {
      id: 'moment-2',
      caption: 'Iris pulls the sword from the stone.',
      imageSrc: 'data:image/png;base64,def',
    };

    act(() => {
      hook.result.current.applyResponseEffects({ sender: 'gamemaster', content: 'The sword slides free.', moment });
    });
    act(() => {
      hook.result.current.dismissMoment();
    });

    expect(hook.result.current.activeMoment).toBeNull();
    expect(hook.result.current.moments).toEqual([moment]);
  });

  it('updates the story summary and unresolved threads from a turn response', async () => {
    const { hook } = setup();
    await loadActiveGame(hook);

    act(() => {
      hook.result.current.applyResponseEffects({
        sender: 'gamemaster',
        content: 'You continue on.',
        storySummary: 'Iris crossed the causeway.',
        unresolvedThreads: ['Find the lantern'],
      });
    });

    expect(hook.result.current.storySummary).toBe('Iris crossed the causeway.');
    expect(hook.result.current.unresolvedThreads).toEqual(['Find the lantern']);
  });
});
