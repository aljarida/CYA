import {
  API_DELETE_GAME_URL,
  API_INITIALIZE_URL,
  API_LOAD_GAME_URL,
} from '../misc/enums';
import type { DraftStartingState } from '../features/setup/setupTypes';
import type { GameInfo, GameSave, LoadMessage, MessageResponse } from '../misc/types';
import { getJson, postJson } from './client';
import { toChatHistoryMessage, toMessageResponse } from './messageMappers';
import type { BackendGameSave, BackendMessage } from './types';

const API_EXISTING_GAMES_URL = 'http://localhost:3000/api/existing_games';

type ExistingGamesResponse = {
  results?: BackendGameSave[];
};

export type GameResponse = MessageResponse & {
  gameId?: string;
  hitPoints: number;
  portraitSrc: string;
  worldBackdropSrc: string;
};

function normalizeGameSave(save: BackendGameSave): GameSave {
  return {
    ...save,
    chatHistory: (save.chatHistory || []).map(toChatHistoryMessage),
  };
}

function normalizeGameResponse(response: BackendMessage & Partial<GameResponse>): GameResponse {
  return toMessageResponse(response) as GameResponse;
}

export async function getExistingGames(): Promise<GameSave[]> {
  const { data } = await getJson<ExistingGamesResponse>(API_EXISTING_GAMES_URL);

  return (data.results || [])
    .map(normalizeGameSave)
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}

export async function deleteGame(gameId: string) {
  return postJson(API_DELETE_GAME_URL, { objectIDString: gameId });
}

export async function initializeGame(gameInfo: GameInfo, draftState?: DraftStartingState) {
  const body = draftState
    ? {
        ...gameInfo,
        startingLocation: draftState.startingLocation,
        startingInventory: draftState.startingInventory,
        startingConditions: draftState.startingConditions,
        attributes: draftState.attributes,
      }
    : gameInfo;
  const result = await postJson<BackendMessage & Partial<GameResponse>>(API_INITIALIZE_URL, body);

  return {
    ...result,
    data: normalizeGameResponse(result.data),
  };
}

export async function loadGame(loadMessage: LoadMessage) {
  const result = await postJson<BackendMessage & Partial<GameResponse>>(API_LOAD_GAME_URL, loadMessage);

  return {
    ...result,
    data: normalizeGameResponse(result.data),
  };
}
