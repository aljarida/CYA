import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { BookOpen } from 'lucide-react';

import useChat from './handlers/usechat';
import { useGameSession } from './features/game/useGameSession';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import Portrait from './components/Portrait';
import HitPoints from './components/HitPoints';
import WorldBackdrop from './components/WorldBackdrop';
import BackButton from './components/BackButton';
import MomentPopup from './components/MomentPopup';
import WorldStatePanel from './features/game/WorldStatePanel';

import type { GameSave } from './misc/types';

function ChatApp() {
  const { messages, input, setInput, sendMessage, addMessage, getInputPriorTo, getInputAfter, clearMessages } = useChat();
  const {
    showModal,
    formSubmitted,
    setupStep,
    draftState,
    setDraftState,
    isRegeneratingDraft,
    portraitSrc,
    worldBackdropSrc,
    hitPoints,
    gameId,
    gameInfo,
    setGameInfo,
    isFormValid,
    setIsFormValid,
    worldState,
    playerAttributes,
    storySummary,
    unresolvedThreads,
    moments,
    activeMoment,
    dismissMoment,
    startOrLoadGame,
    generateDraft,
    regenerateDraft,
    confirmAndStart,
    applyResponseEffects,
    discardItem,
    unloadGame,
  } = useGameSession({ addMessage, clearMessages });

  const [journalOpen, setJournalOpen] = useState(false);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setGameInfo(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFormSubmit = async (selectedSave: GameSave | null) => {
    if (selectedSave) {
      await startOrLoadGame(selectedSave);
    } else {
      await generateDraft(gameInfo);
    }
  };

  const handleSendMessage = async (messageOverride?: string) => {
    const data = await sendMessage(messageOverride, gameId);
    applyResponseEffects(data);
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
  }

  const handleKeyPress = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    switch (e.key) {
      case 'Enter':
        handleSendMessage();
        break;
      case 'ArrowUp':
        setInput(getInputPriorTo(input));
        break;
      case 'ArrowDown':
        setInput(getInputAfter(input));
        break;
    }
  }

  return (
    <div className="relative flex h-screen min-w-0 flex-col overflow-x-hidden bg-gradient-to-br from-neutral-800 via-gray-700 to-neutral-600 px-4 py-6 sm:p-8">
      <SetupModal
        showModal={showModal}
        formSubmitted={formSubmitted}
        gameInfo={gameInfo}
        isFormValid={isFormValid}
        handleInputChange={handleInputChange}
        onSubmit={handleFormSubmit}
        setIsFormValid={setIsFormValid}
        setupStep={setupStep}
        draftState={draftState}
        onDraftChange={setDraftState}
        onRegenerateDraft={regenerateDraft}
        isRegeneratingDraft={isRegeneratingDraft}
        onConfirmDraft={confirmAndStart}
      />

      <WorldBackdrop src={worldBackdropSrc} />
      <Portrait src={portraitSrc} />
      <HitPoints hitPoints={hitPoints} />

      {!showModal && (
        <button
          onClick={() => setJournalOpen(o => !o)}
          className="absolute top-5 left-14 z-10 p-2 rounded-full bg-black/20 hover:bg-black/40 transition-colors duration-200 backdrop-blur-sm"
          title="Journal"
        >
          <BookOpen size={16} className="text-white/70 hover:text-white" />
        </button>
      )}

      <WorldStatePanel
        worldState={worldState}
        playerAttributes={playerAttributes}
        isOpen={journalOpen}
        onClose={() => setJournalOpen(false)}
        onDiscard={discardItem}
        moments={moments}
        storySummary={storySummary}
        unresolvedThreads={unresolvedThreads}
      />

      <MomentPopup moment={activeMoment} onDismiss={dismissMoment} />

      <ChatMessages messages={messages} gameId={gameId} onSuggestionClick={handleSuggestionClick} />
      <ChatInput
        input={input}
        setInput={setInput}
        onSend={handleSendMessage}
        onKeyPress={handleKeyPress}
      />
      <BackButton unloadGame={unloadGame} />
    </div>
  );
}

export default ChatApp;
