import { useState } from "react";

import type { Message, MessageResponse } from "../misc/types";

import { API_RESPONSE_URL } from "../misc/enums";
import postJsonRequest from "../misc/postjsonrequest";

const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const addMessage = ({ sender, content }: Message) => {
    setMessages(prev => [...prev, { sender, content }]);
  };

  const sendMessage = async (): Promise<MessageResponse | null> => {
    if (!input.trim()) return null;

    const userMessage = input;
    addMessage({ sender: 'user', content: userMessage });
    setInput("");

    const result = await postJsonRequest(API_RESPONSE_URL, {
      content: userMessage,
    });
    const data: MessageResponse = result.data

    if (result.ok) {
      addMessage({ sender: data.sender, content: data.content });
      if (data.gameOverSummary !== undefined) {
        addMessage({ sender: 'system', content: data.gameOverSummary })
      }
    } else {
      addMessage({ sender: 'error', content: data.content });
    }

    return data;
  };

  const getInputPriorTo = (input: string) => {
    for (let i = messages.length - 1; i > -1; i--) {
      const inputFound: boolean = (
        messages[i].sender === 'user' &&
        messages[i].content === input
      )

      if (inputFound) {
        for (let j = i - 1; j >= 0; j--) {
          const priorUserInputExists: boolean = messages[j].sender === 'user'
          if (priorUserInputExists) {
            const priorUserInput: string = messages[j].content;
            return priorUserInput;
          }
        }
      }
    }

    for (let i = messages.length - 1; i > -1; i--) {
      if (messages[i].sender === 'user') {
        const firstInput: string = messages[i].content;
        return firstInput;
      }
    }

    return "";
  }


  return {
    messages,
    input,
    setInput,
    sendMessage,
    addMessage,
    getInputPriorTo,
  };
};

export default useChat;
