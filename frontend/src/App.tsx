import { useState } from 'react';

import { API_INITIALIZE_URL, API_LOAD_GAME_URL, MAX_HIT_POINTS } from './misc/enums';
import postJsonRequest from './misc/postjsonrequest';

import useGameInfo from './handlers/usegameinfo';
import useChat from './handlers/usechat';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import Portrait from './components/Portrait';
import HitPoints from './components/HitPoints';
import WorldBackdrop from './components/WorldBackdrop';
import type { ChatHistoryMessage, GameSave, LoadMessage } from './misc/types';

function ChatApp() {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [portraitUrl, setPortraitUrl] = useState<string>("");
  const [worldBackdropUrl, setWorldBackdropUrl] = useState<string>("");
  const [hitPoints, setHitPoints] = useState<number>(-1);

  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, addMessage, getInputPriorTo } = useChat();

  const handleFormSubmit = async (selectedSave: GameSave) => {
    if (!selectedSave && !isFormValid) return;

    setFormSubmitted(true);
    const loadedSavedGame: boolean = selectedSave !== null;
    if (loadedSavedGame) {
      // Load the game save on the backend.
      const loadMessage: LoadMessage = {
        objectIDString: selectedSave.objectIDString
      };
      const result = await postJsonRequest(API_LOAD_GAME_URL, loadMessage);
      console.assert(result.ok, `Fatal error loading game: ${result.data}`)
      const data = result.data;
      addMessage({ "sender": data.sender, "content": data.content })
      
      // Render all prior chats.
      selectedSave.chatHistory.forEach((m: ChatHistoryMessage, idx: number) => {
        if (idx === 0) return;
        addMessage({ sender: m.role, content: m.content });
      });

    } else {
      // Handle initializing a new game.
      const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);
      const data = result.data;

      if (result.ok) {
        setPortraitUrl(data.portraitUrl);
        setWorldBackdropUrl(data.worldBackdropUrl)
        setHitPoints(MAX_HIT_POINTS);

        addMessage({
          sender: 'system',
          content: `Welcome to your adventure, ${gameInfo.playerName}! Simply start typing to get started!`,
        });
      } else {
        addMessage({
          sender: 'error',
          content: data.content,
        });
      }
    }

    setShowModal(false);

  };

  const handleSendMessage = async () => {
    const data = await sendMessage();
    if (data && data.hasOwnProperty('hitPoints') && typeof data.hitPoints == 'number') {
      setHitPoints(data.hitPoints);
    }
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
        setInput("");
        break;
    }
  }

  return (
    <div className="relative flex flex-col h-screen bg-gradient-to-br from-neutral-800 via-gray-700 to-neutral-600 p-8 pr-16">
      <SetupModal
        showModal={showModal}
        formSubmitted={formSubmitted}
        gameInfo={gameInfo}
        isFormValid={isFormValid}
        handleInputChange={handleInputChange}
        onSubmit={handleFormSubmit}
      />

      <WorldBackdrop url={worldBackdropUrl} />
      <Portrait url={portraitUrl} />
      <HitPoints hitPoints={hitPoints} />

      <ChatMessages messages={messages} />
      <ChatInput
        input={input}
        setInput={setInput}
        onSend={handleSendMessage}
        onKeyPress={handleKeyPress}
      />
    </div>
  );
}

export default ChatApp;
