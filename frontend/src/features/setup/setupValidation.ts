import type { GameInfo, GameSave } from '../../misc/types';

export function gameInfoValidationMessage(gameInfo: GameInfo, existingGames: GameSave[]) {
  const playerName = gameInfo.playerName.trim();

  if (
    playerName === '' ||
    gameInfo.worldTheme.trim() === '' ||
    gameInfo.playerDescription.trim() === ''
  ) {
    return 'Please fill out all fields.';
  }
  if (existingGames.find((game) => game.playerName === playerName) !== undefined) {
    return 'A save with that name already exists.';
  }

  return '';
}

export function isValidGameInfo(gameInfo: GameInfo, existingGames: GameSave[]) {
  return gameInfoValidationMessage(gameInfo, existingGames) === '';
}
