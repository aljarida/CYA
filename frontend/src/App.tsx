import { useState } from 'react';
import type { FormEvent } from 'react';

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

  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, handleKeyPress, addMessage } = useChat();

  const handleFormSubmit = async (_: FormEvent) => {
    if (!isFormValid) return;

    setFormSubmitted(true);

    try {
      const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);
      console.log("Initialization succeeded");
      console.log(result);

      setPortraitUrl(result.portraitUrl);
      setShowModal(false);

      addMessage({
        sender: 'system',
        content: `Welcome to your adventure, ${gameInfo.playerName}! Simply start typing to get started!`,
      });
    } catch (error) {
      console.log(error);
    }
  };

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

      <ChatMessages messages={messages} />

      <ChatInput
        input={input}
        setInput={setInput}
        onSend={sendMessage}
        onKeyPress={handleKeyPress}
      />
    </div>
  );
}

export default ChatApp;

