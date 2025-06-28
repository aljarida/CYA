// src/components/SetupForm.tsx
import { useState } from 'react'
import type { SetupFormProps, GameSave } from '../misc/types'
import FormField from './FormField'
import pretty_timestamp from '../misc/pretty_timestamp.ts'


function SetupForm({
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit,
  existingGames,
  isLoadingSaves,
  selectedSave,
  setSelectedSave,
  deleteGame,
}: SetupFormProps) {
  const [clickedDelete, setClickedDelete] = useState<boolean>(false);
  function requestDelete(save: GameSave) {
    if (clickedDelete) {
      deleteGame(save);
    }

    if (!clickedDelete) {
      setClickedDelete(true);
      setTimeout(() => setClickedDelete(false), 2000);
    }
  }

  return (
    <>
      <h2 className="text-2xl font-bold text-neutral-200 mb-6">Adventure Setup</h2>

      {isLoadingSaves ? (
        <p className="text-neutral-400">Loading game saves…</p>
      ) : existingGames.length > 0 ? (
        <div className="mb-6">
          <label className="block text-neutral-300 mb-2">Load Existing Game</label>
          <select
            className="w-full p-2 rounded-md bg-neutral-800 text-neutral-100"
            value={selectedSave?.objectIDString || ''}
            onChange={(e) => {
              const save = existingGames.find(g => g.objectIDString === e.target.value) || null
              setSelectedSave(save)
            }}
          >
            <option value="">Start New Adventure</option>
            {existingGames.map((g: GameSave) => (
              <option key={g.objectIDString} value={g.objectIDString}>
                {g.playerName} - {pretty_timestamp(g.updatedAt)}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {selectedSave ? (
        <>
          <button
            onClick={() => requestDelete(selectedSave)}
            className={`w-full py-3 mt-4 bg-red-700/60 hover:bg-red-600/60
              rounded-lg text-white shadow-md transition-colors
              ${clickedDelete ? 'animate-pulse' : ''}`}
            style={clickedDelete ? { animationDuration: '0.5s' } : undefined}
          >
            {clickedDelete ? "Confirm Deletion" : "Delete Adventure"}
          </button>
          <button
            onClick={() => onSubmit(selectedSave)}
            className="w-full py-3 mt-4 bg-green-700/60 hover:bg-green-600/60 rounded-lg text-white shadow-md transition-colors"
          >
            Continue Adventure
          </button>
        </>
      ) : (
        <div className="space-y-5">
          <FormField
            id="playerName"
            name="playerName"
            label="Player Name"
            value={gameInfo.playerName}
            onChange={handleInputChange}
            placeholder="Enter your name"
            required
          />

          <FormField
            id="worldTheme"
            name="worldTheme"
            label="Game Theme"
            value={gameInfo.worldTheme}
            onChange={handleInputChange}
            placeholder="Detail the game world"
            required
          />

          <FormField
            id="playerDescription"
            name="playerDescription"
            label="Description of Player Character"
            value={gameInfo.playerDescription}
            onChange={handleInputChange}
            placeholder="Describe your character"
            required
          />

          <button
            onClick={() => onSubmit(null)}
            disabled={!isFormValid}
            className={`w-full py-3 rounded-lg shadow-lg mt-4 transition-colors backdrop-blur-sm ${
              isFormValid
                ? 'bg-green-700/70 hover:bg-green-600/70 text-neutral-200 border border-neutral-600/50'
                : 'bg-neutral-800/60 text-neutral-500 cursor-not-allowed border border-neutral-700/30'
            }`}
          >
            Begin Adventure
          </button>
        </div>
      )}
    </>
  )
}

export default SetupForm
