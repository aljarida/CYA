// src/components/SetupModal.tsx
import { useState, useEffect } from 'react'
import type { SetupModalProps, GameSave } from '../misc/types'
import LoadingState from './LoadingState'
import SetupForm from './SetupForm'

import postJsonRequest from '../misc/postjsonrequest.ts';
import { API_DELETE_GAME_URL } from '../misc/enums.ts';

function SetupModal({
  showModal,
  formSubmitted,
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit,
  setIsFormValid,
}: SetupModalProps) {
  const [existingGames, setExistingGames] = useState<GameSave[]>([]);
  const [isLoadingSaves, setIsLoadingSaves] = useState<boolean>(false);
  const [selectedSave, setSelectedSave] = useState<GameSave | null>(null);
  
  useEffect(() => {
    setIsFormValid(
      gameInfo.playerName.trim() !== "" && 
      gameInfo.worldTheme.trim() !== "" &&
      gameInfo.playerDescription.trim() !== "" &&
      (existingGames.find(g => (g.playerName === gameInfo.playerName.trim())) === undefined)
    );
  }, [gameInfo]);
  
  const deleteGame = async (g: GameSave) => {
    const res = await postJsonRequest(API_DELETE_GAME_URL, { "objectIDString": g.objectIDString })
    console.assert(res.ok, "Status: ", res.status, "Data: ", res.data)
    setSelectedSave(null)
    setExistingGames(prev => prev.filter(game => game.objectIDString != g.objectIDString));
  };
  
  useEffect(() => {
    if (!showModal) return

    setIsLoadingSaves(true)
    fetch('http://localhost:3000/api/existing_games')
      .then(res => res.json())
      .then(data => {
        const sorted: GameSave[] = (data.results || []).sort(
          (a: GameSave, b: GameSave) =>
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
        )
        setExistingGames(sorted)
      })
      .catch(() => setExistingGames([]))
      .finally(() => setIsLoadingSaves(false))
  }, [showModal])

  if (!showModal) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-neutral-900/90 backdrop-blur-md rounded-xl p-8 shadow-2xl w-full max-w-md relative border border-neutral-700/50">
        {formSubmitted ? (
          <LoadingState />
        ) : (
          <SetupForm
            gameInfo={gameInfo}
            isFormValid={isFormValid}
            handleInputChange={handleInputChange}
            onSubmit={onSubmit}
            existingGames={existingGames}
            isLoadingSaves={isLoadingSaves}
            selectedSave={selectedSave}
            setSelectedSave={setSelectedSave}
            deleteGame={deleteGame}
          />
        )}
      </div>
    </div>
  )
}

export default SetupModal
