import { describe, expect, it } from 'vitest';

import type { GameSave } from '../../misc/types';
import { gameInfoValidationMessage, isValidGameInfo } from './setupValidation';

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

describe('isValidGameInfo', () => {
  it('requires all fields after trimming whitespace', () => {
    expect(isValidGameInfo({
      playerName: 'Mira',
      worldTheme: ' ',
      playerDescription: 'A careful cartographer',
    }, [])).toBe(false);
  });

  it('rejects duplicate existing player names', () => {
    expect(isValidGameInfo({
      playerName: ' Mira ',
      worldTheme: 'Sky islands',
      playerDescription: 'A careful cartographer',
    }, [save])).toBe(false);
  });

  it('accepts complete non-duplicate game info', () => {
    expect(isValidGameInfo({
      playerName: 'Sol',
      worldTheme: 'Sky islands',
      playerDescription: 'A careful cartographer',
    }, [save])).toBe(true);
  });

  it('explains why game info is invalid', () => {
    expect(gameInfoValidationMessage({
      playerName: 'Foo',
      worldTheme: '',
      playerDescription: '',
    }, [])).toBe('Please fill out all fields.');

    expect(gameInfoValidationMessage({
      playerName: ' Mira ',
      worldTheme: 'Sky islands',
      playerDescription: 'A careful cartographer',
    }, [save])).toBe('A save with that name already exists.');
  });
});
