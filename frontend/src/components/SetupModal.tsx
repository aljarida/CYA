import type { SetupModalProps } from '../misc/types';
import LoadingState from './LoadingState';
import SetupForm from './SetupForm';

function SetupModal({
  showModal,
  formSubmitted,
  gameInfo,
  isFormValid,
  handleInputChange,
  onSubmit
}: SetupModalProps) {
  if (!showModal) return null;

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
          />
        )}
      </div>
    </div>
  );
};

export default SetupModal;