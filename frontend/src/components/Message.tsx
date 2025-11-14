import { useState, useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import type { MessageProps } from "../misc/types";
import { API_GET_SUGGESTED_RESPONSES_URL } from '../misc/enums';
import getJsonRequest from '../misc/getjsonrequest';

function Message({ message, index, gameId, onSuggestionClick }: MessageProps) {
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const messageRef = useRef<HTMLDivElement>(null);
    const suggestionsRef = useRef<HTMLDivElement>(null);

    // Handle click-away to hide suggestions
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                showSuggestions &&
                messageRef.current &&
                suggestionsRef.current &&
                !messageRef.current.contains(event.target as Node) &&
                !suggestionsRef.current.contains(event.target as Node)
            ) {
                setShowSuggestions(false);
            }
        };

        if (showSuggestions) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [showSuggestions]);

    const handleGetSuggestions = async (e: React.MouseEvent) => {
        e.stopPropagation();
        
        if (!gameId || isLoadingSuggestions) return;

        setIsLoadingSuggestions(true);
        setShowSuggestions(true);

        try {
            const result = await getJsonRequest(API_GET_SUGGESTED_RESPONSES_URL, {
                gameId: gameId,
                n: 3
            });

            if (result.ok && result.data.suggestions) {
                setSuggestions(result.data.suggestions);
            } else {
                setSuggestions([]);
            }
        } catch (error) {
            console.error('Failed to fetch suggestions:', error);
            setSuggestions([]);
        } finally {
            setIsLoadingSuggestions(false);
        }
    };

    const handleSuggestionClick = (suggestion: string) => {
        setShowSuggestions(false);
        onSuggestionClick(suggestion);
    };

    const isGamemasterMessage = message.sender === 'gamemaster';

    return (
        <div className={`relative flex flex-col ${message.sender === 'user' ? 'items-end' : 'items-start'}`}>
            <div 
                ref={messageRef}
                className={`p-4 rounded-lg w-fit max-w-lg relative ${
                    message.sender === 'user' 
                        ? 'bg-neutral-800/70 text-neutral-300' 
                        : message.sender == 'system'
                            ? 'bg-gray-600/10 text-indigo-200'
                            : message.sender == 'error'
                                ? 'bg-gray-600/10 text-red-300'
                                : 'bg-neutral-700/70 text-neutral-200'
                } backdrop-blur-sm shadow-lg`}
            >              
                <p className="text-sm break-words whitespace-pre-line">{message.content}</p>
                
                {isGamemasterMessage && (
                    <button
                        onClick={handleGetSuggestions}
                        className="absolute bottom-2 right-2 p-1.5 rounded-full bg-neutral-600/50 hover:bg-neutral-600/80 transition-colors duration-200 backdrop-blur-sm"
                        title="Get suggested responses"
                    >
                        <Sparkles size={14} className="text-neutral-300" />
                    </button>
                )}

                {showSuggestions && isGamemasterMessage && (
                    <div 
                        ref={suggestionsRef}
                        className="absolute left-full ml-4 -top-8 flex flex-col gap-2 z-50 min-w-[200px] max-w-[300px]"
                    >
                    {isLoadingSuggestions ? (
                        <div className="bg-neutral-800/90 text-neutral-300 p-3 rounded-lg shadow-lg backdrop-blur-sm">
                            <p className="text-xs">Loading suggestions...</p>
                        </div>
                    ) : suggestions.length > 0 ? (
                        suggestions.map((suggestion, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="bg-neutral-800/90 hover:bg-neutral-700/90 text-neutral-200 p-3 rounded-lg shadow-lg backdrop-blur-sm text-left text-sm transition-colors duration-200 border border-neutral-700/50 hover:border-neutral-600/50"
                            >
                                {suggestion}
                            </button>
                        ))
                    ) : (
                        <div className="bg-neutral-800/90 text-neutral-400 p-3 rounded-lg shadow-lg backdrop-blur-sm">
                            <p className="text-xs">No suggestions available</p>
                        </div>
                    )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Message;
