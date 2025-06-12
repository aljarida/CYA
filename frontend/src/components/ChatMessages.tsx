import { useEffect, useRef } from 'react';
import type { ChatMessagesProps } from '../misc/types';
import Message from './Message'

function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth'});
  }, [messages])

  return ( 
    <div className="flex flex-col flex-grow space-y-4 bg-neutral-900/50 rounded-xl p-6 overflow-y-auto shadow-md backdrop-blur-sm">
      {messages.map((message, index) => (
        <Message key={index} message={message} index={index} />
      ))}
    <div ref={bottomRef} />
    </div>
  )
};

export default ChatMessages;