import { API_RESPONSE_URL } from '../misc/enums';
import type { MessageResponse } from '../misc/types';
import { postJson } from './client';
import { toMessageResponse } from './messageMappers';
import type { BackendMessage } from './types';

export async function sendChatMessage(content: string, gameId: string) {
  const result = await postJson<BackendMessage & Partial<MessageResponse>>(API_RESPONSE_URL, {
    content,
    gameId,
  });

  return {
    ...result,
    data: toMessageResponse(result.data),
  };
}
