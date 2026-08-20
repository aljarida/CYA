import { useEffect, useState } from 'react';

import { deleteGame as deleteSavedGame, getExistingGames } from '../../api/games';
import type { GameSave } from '../../misc/types';

export function useSavedGames(showModal: boolean) {
  const [existingGames, setExistingGames] = useState<GameSave[]>([]);
  const [isLoadingSaves, setIsLoadingSaves] = useState<boolean>(false);
  const [selectedSave, setSelectedSave] = useState<GameSave | null>(null);

  useEffect(() => {
    if (!showModal) return;

    setIsLoadingSaves(true);
    getExistingGames()
      .then(setExistingGames)
      .catch(() => setExistingGames([]))
      .finally(() => setIsLoadingSaves(false));
  }, [showModal]);

  const deleteGame = async (save: GameSave) => {
    const res = await deleteSavedGame(save.objectIDString);
    console.assert(res.ok, 'Status: ', res.status, 'Data: ', res.data);
    setSelectedSave(null);
    setExistingGames((prev) => prev.filter((game) => game.objectIDString !== save.objectIDString));
  };

  return {
    existingGames,
    isLoadingSaves,
    selectedSave,
    setSelectedSave,
    deleteGame,
  };
}
