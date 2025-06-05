import type { ChatInputProps } from "../misc/types";

function ChatInput({ input, setInput, onSend, onKeyPress }: ChatInputProps) {
  return (
    <div className="flex mt-4">
        <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyPress}
        placeholder="What would you like to do?"
        className="flex-1 p-3 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 shadow-lg"
        />
        <button 
        onClick={onSend} 
        className="ml-2 px-4 py-2 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm shadow-lg hover:outline-none hover:ring-2 hover:ring-neutral-500 transition-colors"
        >
        Send
        </button>
    </div>
  )
};

export default ChatInput;
