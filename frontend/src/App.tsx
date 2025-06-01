import { useState } from 'react';
import type { FormEvent } from 'react';

import { FORM_SUBMIT_DELAY } from './misc/enums';

import useGameInfo from './handlers/usegameinfo';
import useChat from './handlers/usechat';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';

function ChatApp() {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  
  const { gameInfo, isFormValid, handleInputChange } = useGameInfo();
  const { messages, input, setInput, sendMessage, handleKeyPress, addMessage } = useChat(gameInfo);

  const handleFormSubmit = (e: FormEvent) => {
    if (!isFormValid) return;
    
    setFormSubmitted(true);
    
    setTimeout(() => {
      // TODO: Submit a post request to modify the game state with the game info.
      setShowModal(false);
      console.log("Handling form submission");
      console.log(gameInfo);
      addMessage('system', "Handled form submission. Check console.");
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