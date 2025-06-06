import { useState } from 'react';
import type { FormEvent } from 'react';

import { Heart, HeartCrack } from 'lucide-react';

import { API_INITIALIZE_URL } from './misc/enums';

import useGameInfo from './handlers/usegameinfo';
import useChat from './handlers/usechat';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import postJsonRequest from './misc/postjsonrequest';

function ChatApp() {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [portraitUrl, setPortraitUrl] = useState<string | null>(null);
  const [hitPoints, setHitPoints] = useState<number>(-1);

  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, handleKeyPress, addMessage } = useChat();

  const handleFormSubmit = async (_: FormEvent) => {
    if (!isFormValid) return;

    setFormSubmitted(true);

    try {
      const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);

      setPortraitUrl(result.portraitUrl);
      setShowModal(false);
	  setHitPoints(5); // TODO: Should not be magic.

      addMessage({
        sender: 'system',
        content: `Welcome to your adventure, ${gameInfo.playerName}! Simply start typing to get started!`,
      });
    } catch (error) {
      addMessage({
        sender: 'error',
        content: error,
      });
    }
  };

  // TODO: Similar to the TODO below; fix the architecture.
  const handleSendMessage = async() => {
	  console.log("handleSendMessage called!")
	  const result = await sendMessage();
	  console.log(result)

	  if (result.hasOwnProperty('hitPoints') && typeof result.hitPoints == 'number') {
		  setHitPoints(result.hitPoints);
	  }
  }

  // TODO: Instead of shadowing handleKeyPress, fix the architecture.
  const handleKeyPress_ = async(e: any) => {
	if (e.key === 'Enter') {
		handleSendMessage();
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

	{portraitUrl && (
	  <div className="absolute top-4 right-8 border-4 w-20 h-20 z-2 rounded-xl backdrop-blur-sm shadow-xl border border-white/20 hover:outline-none hover:ring-2 hover:ring-neutral-500">
		<img
		  src={portraitUrl}
		  alt="Player Portrait"
		  className="w-full h-full object-cover rounded-lg"
		/>
	  </div>
	)}

	{hitPoints >= 0 && (
  <div className="absolute top-26 right-8 flex gap-1 w-20 justify-end">
    {Array.from({ length: 5 }).map((_, i) =>
      i < 5 - hitPoints ? (
        // Broken heart (lost health)
        <HeartCrack key={i} className="w-4 h-4 z-3 text-red-400" />
      ) : (
        // Full heart
        <Heart key={i} className="w-4 h-4 z-3 text-red-400 fill-current stroke-none" />
      )
    )}
  </div>
)}


      <ChatMessages messages={messages} />

      <ChatInput
        input={input}
        setInput={setInput}
        onSend={handleSendMessage}
        onKeyPress={handleKeyPress_}
      />
    </div>
  );
}

export default ChatApp;

