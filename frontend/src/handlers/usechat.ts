import { useState } from "react";

import postJsonRequest from "../misc/postjsonrequest";

const useChat = (gameInfo) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const addMessage = (sender, content) => {
    setMessages(prev => [...prev, { sender, content }]);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage = input;
    addMessage('user', userMessage);
    setInput("");

    try {
      const result = await postJsonRequest(API_URL, {
        content: userMessage,
        gameInfo
      });
      
      addMessage('system', result.content);
    } catch (error) {
      addMessage('system', "Error fetching message");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  };

  return {
    messages,
    input,
    setInput,
    sendMessage,
    handleKeyPress,
    addMessage
  };
};

export default useChat;