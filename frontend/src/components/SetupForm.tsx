import type { SetupFormProps } from '../misc/types';
import FormField from './FormField';

function SetupForm({
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit
}: SetupFormProps) {
  return <>
    <h2 className="text-2xl font-bold text-neutral-200 mb-6">Adventure Setup</h2>
    <div onSubmit={onSubmit}>
      <div className="space-y-4">
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
          placeholder="Fantasy, Sci-fi, Horror, etc."
          required
        />
        
        <FormField
          id="playerDescription"
          name="playerDescription"
          label="Description of Player Character (optional)"
          value={gameInfo.playerDescription}
          onChange={handleInputChange}
          placeholder="Describe your character"
          isTextarea
        />
        
        <FormField
          id="worldDescription"
          name="worldDescription"
          label="Description of World (optional)"
          value={gameInfo.worldDescription}
          onChange={handleInputChange}
          placeholder="Describe the game world"
          isTextarea
        />
        
        <button
          onClick={onSubmit}
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
    </div>
  </>
};

export default SetupForm;