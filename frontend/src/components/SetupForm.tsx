// src/components/SetupForm.tsx
import type { SetupFormProps } from '../misc/types'
import FormField from './FormField'

export type GameSave = {
  playerName: string
  playerDescription: string
  worldTheme: string
  gameOverSummary: string
  gameOver: boolean
  createdAt: string
  updatedAt: string
  objectIDString: string
  chatHistory: any[]
}

export interface UpdatedSetupFormProps extends SetupFormProps {
  existingGames: GameSave[]
  isLoadingSaves: boolean
  selectedSave: GameSave | null
  setSelectedSave: (save: GameSave | null) => void
}

const SetupForm = ({
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit,
  existingGames,
  isLoadingSaves,
  selectedSave,
  setSelectedSave
}: UpdatedSetupFormProps) => {
  return (
    <>
      <h2 className="text-2xl font-bold text-neutral-200 mb-6">Adventure Setup</h2>

      {isLoadingSaves ? (
        <p className="text-neutral-400">Loading saved games…</p>
      ) : existingGames.length > 0 ? (
        <div className="mb-6">
          <label className="block text-neutral-300 mb-2">Load Existing Game</label>
          <select
            className="w-full p-2 rounded-md bg-neutral-800 text-neutral-100"
            value={selectedSave?.objectIDString || ''}
            onChange={(e) => {
              const sel = existingGames.find(g => g.objectIDString === e.target.value) || null
              setSelectedSave(sel)
            }}
          >
            <option value="">— Start New Adventure —</option>
            {existingGames.map((g) => (
              <option key={g.objectIDString} value={g.objectIDString}>
                {g.playerName} — {g.worldTheme}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {selectedSave ? (
        <button
          onClick={() => onSubmit(selectedSave)}
          className="w-full py-3 mt-4 bg-green-700 hover:bg-green-600 rounded-lg text-white shadow-md transition-colors"
        >
          Continue Adventure
        </button>
      ) : (
        <div>
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
                ? 'bg-neutral-700/80 hover:bg-neutral-600/80 text-neutral-200 border border-neutral-600/50'
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
