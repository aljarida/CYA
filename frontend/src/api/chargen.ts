import { API_GENERATE_STARTING_STATE_URL } from '../misc/enums';
import type { DraftStartingState } from '../features/setup/setupTypes';
import type { GameInfo } from '../misc/types';
import { postJson } from './client';

export async function generateStartingState(gameInfo: GameInfo) {
  return postJson<DraftStartingState>(API_GENERATE_STARTING_STATE_URL, gameInfo);
}
