import { useState } from "react";

import type { Message, MessageResponse } from "../misc/types";

import { API_RESPONSE_URL } from "../misc/enums";
import postJsonRequest from "../misc/postjsonrequest";

const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };
  
  const clearMessages = () => {
    setMessages([]);
  }

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

  const getInputPriorTo = (givenMsg: string) => {
    const noGivenMsg: boolean = givenMsg === "";
    let usrMsgFound: boolean = false;

    let i = messages.length - 1;
    for (; i > -1; i--) {
      usrMsgFound = (messages[i].sender === 'user');
      if (usrMsgFound && noGivenMsg) {
        return messages[i].content;
      } else if (usrMsgFound && messages[i].content === input) {
        break;
      }
    }

    if (usrMsgFound) {
      for (let j = i - 1; j >= 0; j--) {
        const priorUsrMsg: boolean = messages[j].sender === 'user';
        if (priorUsrMsg) return messages[j].content;
      }
    }

    return "";
  }
  
  const getInputAfter = (givenMsg: string) => {
    const noGivenMsg: boolean = givenMsg === "";
    let usrMsgFound: boolean = false;

    let i = 0;
    for (; i < messages.length; i++) {
      usrMsgFound = (messages[i].sender === 'user');
      if (usrMsgFound && noGivenMsg) {
        return messages[i].content;
      } else if (usrMsgFound && messages[i].content === input) {
        break;
      }
    }

    if (usrMsgFound) {
      for (let j = i + 1; j < messages.length; j++) {
        const nextUsrMsg: boolean = messages[j].sender === 'user';
        if (nextUsrMsg) return messages[j].content;
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
	  getInputAfter,
    clearMessages,
  };
};

export default useChat;
