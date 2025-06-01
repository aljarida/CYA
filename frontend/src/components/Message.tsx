import type { MessageProps } from "../misc/types";

function Message({ message, index }: MessageProps) { 
    return (
        <div 
            key={index} 
            className={`p-4 rounded-lg w-fit max-w-lg ${
            message.sender === 'user' 
                ? 'bg-neutral-800/80 text-neutral-200 self-end' 
                : 'bg-neutral-700/80 text-neutral-300 self-start'
            } backdrop-blur-sm shadow-lg`}
        >              
            <p className="text-sm break-words whitespace-pre-line">{message.content}</p>
        </div>
    )
};

export default Message;