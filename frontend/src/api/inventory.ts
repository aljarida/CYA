import { API_DISCARD_ITEM_URL } from '../misc/enums';
import type { MessageResponse } from '../misc/types';
import { postJson } from './client';
import { toMessageResponse } from './messageMappers';
import type { BackendMessage } from './types';

export async function discardItem(gameId: string, itemId: string) {
  const result = await postJson<BackendMessage & Partial<MessageResponse>>(API_DISCARD_ITEM_URL, {
    gameId,
    itemId,
  });

  return {
    ...result,
    data: toMessageResponse(result.data),
  };
}
