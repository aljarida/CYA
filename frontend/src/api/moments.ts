import { API_MOMENTS_URL } from '../misc/enums';
import type { StoryMoment } from '../misc/types';
import { getJson } from './client';

type MomentsResponse = {
  results?: StoryMoment[];
};

export async function getMoments(gameId: string): Promise<StoryMoment[]> {
  const { data } = await getJson<MomentsResponse>(API_MOMENTS_URL, { gameId });

  return data.results || [];
}
