import { API_GET_SUGGESTED_RESPONSES_URL } from '../misc/enums';
import { getJson } from './client';

type SuggestedResponses = {
  suggestions?: string[];
};

export async function getSuggestedResponses(gameId: string, n = 3): Promise<string[]> {
  const result = await getJson<SuggestedResponses>(API_GET_SUGGESTED_RESPONSES_URL, { gameId, n });

  if (!result.ok || !result.data?.suggestions) return [];
  return result.data.suggestions;
}
