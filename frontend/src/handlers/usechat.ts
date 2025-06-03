import { useState } from "react";

import type { Message } from "../misc/types";

import { API_RESPONSE_URL } from "../misc/enums";
import postJsonRequest from "../misc/postjsonrequest";

const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const addMessage = ({ sender, content }: Message) => {
    setMessages(prev => [...prev, { sender, content }]);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMessage = input;
    addMessage({ sender: 'user', content: userMessage });
    setInput("");

    try {
      const result = await postJsonRequest(API_RESPONSE_URL, {
        content: userMessage,
      });
      
      addMessage({ sender: 'system', content: result.content });
    } catch (error) {
      addMessage({ sender: 'system', content: "Error fetching message" });
    }
  };

  const handleKeyPress = (e: any) => {
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