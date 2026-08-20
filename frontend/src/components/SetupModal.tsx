// src/components/SetupModal.tsx
import { useEffect } from 'react'
import type { SetupModalProps } from '../misc/types'
import LoadingState from './LoadingState'
import SetupForm from './SetupForm'
import CharacterSetupSummary from '../features/setup/CharacterSetupSummary'
import { isValidGameInfo } from '../features/setup/setupValidation'
import { useSavedGames } from '../features/setup/useSavedGames'

function SetupModal({
  showModal,
  formSubmitted,
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit,
  setIsFormValid,
  setupStep,
  draftState,
  onDraftChange,
  onRegenerateDraft,
  isRegeneratingDraft,
  onConfirmDraft,
}: SetupModalProps) {
  const {
    existingGames,
    isLoadingSaves,
    selectedSave,
    setSelectedSave,
    deleteGame,
  } = useSavedGames(showModal);

  useEffect(() => {
    setIsFormValid(isValidGameInfo(gameInfo, existingGames));
  }, [existingGames, gameInfo, setIsFormValid]);

  if (!showModal) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-neutral-900/90 backdrop-blur-md rounded-xl p-8 shadow-2xl w-full max-w-md relative border border-neutral-700/50">
        {formSubmitted ? (
          <LoadingState />
        ) : setupStep === 'summary' && draftState ? (
          <CharacterSetupSummary
            draftState={draftState}
            onChange={onDraftChange}
            onRegenerate={onRegenerateDraft}
            onConfirm={onConfirmDraft}
            isRegenerating={isRegeneratingDraft}
          />
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
