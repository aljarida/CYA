import type { ChatMessagesProps } from '../misc/types';
import Message from './Message'

function ChatMessages({ messages }: ChatMessagesProps) {
  return ( 
    <div className="flex flex-col flex-grow space-y-4 bg-neutral-900/80 rounded-xl p-6 overflow-y-auto shadow-md backdrop-blur-md">
      {messages.map((message, index) => (
        <Message key={index} message={message} index={index} />
      ))}
    </div>
  )
};

export default ChatMessages;