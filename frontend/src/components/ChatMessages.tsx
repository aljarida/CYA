import { useEffect, useRef, useState } from 'react';
import { EyeOff } from 'lucide-react';
import type { ChatMessagesProps } from '../misc/types';
import Message from './Message'

function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const [isFaded, setIsFaded] = useState(false)
  
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth'});
  }, [messages])
  
  return (
    <div className="relative flex flex-col flex-grow">
      <button
        onClick={() => setIsFaded(!isFaded)}
        className="absolute top-4 right-16 z-10 p-2 rounded-full bg-black/20 hover:bg-black/40 transition-colors duration-200 backdrop-blur-sm"
      >
        <EyeOff size={16} className="text-white/70 hover:text-white" />
      </button>
      
      <div className={`flex flex-col flex-grow space-y-4 bg-neutral-900/60 rounded-xl p-6 overflow-y-auto shadow-md backdrop-blur-sm transition-opacity duration-500 ${isFaded ? 'opacity-0' : 'opacity-100'}`}>
        {messages.map((message, index) => (
          <Message key={index} message={message} index={index} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
};

export default ChatMessages;