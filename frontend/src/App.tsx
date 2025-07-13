import { useState } from 'react';

import { API_INITIALIZE_URL, API_LOAD_GAME_URL, } from './misc/enums';
import postJsonRequest from './misc/postjsonrequest';

import useChat from './handlers/usechat';

import SetupModal from './components/SetupModal';
import ChatMessages from './components/ChatMessages';
import ChatInput from './components/ChatInput';
import Portrait from './components/Portrait';
import HitPoints from './components/HitPoints';
import WorldBackdrop from './components/WorldBackdrop';
import BackButton from './components/BackButton';

import type { ChatHistoryMessage, GameSave, LoadMessage } from './misc/types';

function ChatApp() {
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [portraitSrc, setPortraitSrc] = useState<string>("");
  const [worldBackdropSrc, setWorldBackdropSrc] = useState<string>("");
  const [hitPoints, setHitPoints] = useState<number>(-1);

  const { messages, input, setInput, sendMessage, addMessage, getInputPriorTo, getInputAfter, clearMessages } = useChat();
  

  const emptyGameInfo = {
    playerName: "",
    worldTheme: "",
    playerDescription: "",
  }

  const [gameInfo, setGameInfo] = useState(emptyGameInfo);

  const [isFormValid, setIsFormValid] = useState(false);

  const handleInputChange = (e: any) => {
    const { name, value } = e.target;
    setGameInfo(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFormSubmit = async (selectedSave: GameSave | null) => {
    if (!selectedSave && !isFormValid) return;

    let data;
    setFormSubmitted(true);
    if (selectedSave !== null) {
      // Load the game save on the backend.
      const loadMessage: LoadMessage = {
        objectIDString: selectedSave.objectIDString
      };
      const result = await postJsonRequest(API_LOAD_GAME_URL, loadMessage);
      console.assert(result.ok, `Fatal error loading game: ${result.data}`)
      data = result.data;
      addMessage({ "sender": data.sender, "content": data.content })
      
      // Render all prior chats.
      selectedSave.chatHistory.forEach((m: ChatHistoryMessage, idx: number) => {
        if (idx === 0) return;
        addMessage({ sender: m.role, content: m.content });
      });

      if (selectedSave.gameOverSummary) {
        addMessage({ "sender": "system", "content": "Oh, no! Unfortunately, you have died!"})
        addMessage({ "sender": "system", "content": selectedSave.gameOverSummary })
      }

    } else {
      // Handle initializing a new game.
      const result = await postJsonRequest(API_INITIALIZE_URL, gameInfo);
      data = result.data;

      if (result.ok) {

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

    setHitPoints(data.hitPoints);
    setPortraitSrc(data.portraitSrc);
    setWorldBackdropSrc(data.worldBackdropSrc)
    setShowModal(false);
    setGameInfo(emptyGameInfo)
  };

  const handleSendMessage = async () => {
    const data = await sendMessage();
    if (data && data.hasOwnProperty('hitPoints') && typeof data.hitPoints == 'number') {
      const lostHitpoints: number = hitPoints - data.hitPoints;
      if (lostHitpoints) {
        setHitPoints(data.hitPoints);
        if (data.hitPoints > 0) {
          addMessage({ "sender": "system", "content": `You lost ${lostHitpoints} health!` })
        }
      }
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
        setInput(getInputAfter(input));
        break;
    }
  }

  const unloadGame = () => {
     // 1. Remove chats 
    clearMessages();
     // 2. Remove portrait
     setPortraitSrc("");
     // 3. Remove backdrop
     setWorldBackdropSrc("");
     // 4. Show modal 
     setFormSubmitted(false); 
     setShowModal(true);
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
        setIsFormValid={setIsFormValid}
      />

      <WorldBackdrop src={worldBackdropSrc} />
      <Portrait src={portraitSrc} />
      <HitPoints hitPoints={hitPoints} />

      <ChatMessages messages={messages} />
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
