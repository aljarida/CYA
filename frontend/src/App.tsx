import { useState } from 'react';
import type { FormEvent } from 'react';

import { API_INITIALIZE_URL, MAX_HIT_POINTS } from './misc/enums';

import useGameInfo from './handlers/usegameinfo';
import useChat from './handlers/usechat';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import postJsonRequest from './misc/postjsonrequest';
import Portrait from './components/Portrait';
import HitPoints from './components/HitPoints';
import WorldBackdrop from './components/WorldBackdrop';

function ChatApp() {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [portraitUrl, setPortraitUrl] = useState<string>("");
  const [worldBackdropUrl, setWorldBackdropUrl] = useState<string>("");
  const [hitPoints, setHitPoints] = useState<number>(-1);

  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, addMessage, getInputPriorTo } = useChat();

  const handleFormSubmit = async (_: FormEvent) => {
    if (!isFormValid) return;

    setFormSubmitted(true);

    const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);
    const data = result.data;

    if (result.ok) {
      setPortraitUrl(data.portraitUrl);
      setWorldBackdropUrl(data.worldBackdropUrl)
      setShowModal(false);
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

