import type { MessageProps } from "../misc/types";

function Message({ message, index }: MessageProps) { 
    return (
        <div 
            key={index} 
            className={`p-4 rounded-lg w-fit max-w-lg ${
            message.sender === 'user' 
                ? 'bg-neutral-800/70 text-neutral-300 self-end' 
                : message.sender == 'system'
					? 'bg-gray-600/10 text-indigo-200 self-start'
					: message.sender == 'error'
						? 'bg-gray-600/10 text-red-300 self-start'
						: 'bg-neutral-700/70 text-neutral-200 self-start'
            } backdrop-blur-sm shadow-lg`}
        >              
            <p className="text-sm break-words whitespace-pre-line">{message.content}</p>
        </div>
    )
};

export default Message;
