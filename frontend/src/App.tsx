import { useState } from 'react';
import type { FormEvent } from 'react';

import { FORM_SUBMIT_DELAY } from './misc/enums';
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
  
  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, handleKeyPress, addMessage } = useChat();

  const handleFormSubmit = (_: FormEvent) => {
    if (!isFormValid) return;
    
    setFormSubmitted(true);
    
    setTimeout(async () => {
      // TODO: Submit a post request to modify the game state with the game info.
      setShowModal(false);
      console.log("Handling form submission");

      try {
        const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);
        console.log("Received result", result)
      } catch (error) {
        console.log(error)
      }

      console.log(gameInfo);
      addMessage({ sender: 'system', content: "Handled form submission. Check console." });
    }, FORM_SUBMIT_DELAY);
  };

  return (
    <div className="relative flex flex-col h-screen bg-gradient-to-br from-neutral-800 via-gray-700 to-neutral-600 p-8">
      <SetupModal
        showModal={showModal}
        formSubmitted={formSubmitted}
        gameInfo={gameInfo}
        isFormValid={isFormValid}
        handleInputChange={handleInputChange}
        onSubmit={handleFormSubmit}
      />
      
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