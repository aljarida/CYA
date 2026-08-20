import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import type { MessageProps } from "../misc/types";
import { getSuggestedResponses } from '../api/suggestions';

function uniqueSuggestions(values: string[]) {
    const seen = new Set<string>();
    return values
        .map((value) => value.trim())
        .filter((value) => {
            if (!value || seen.has(value)) return false;
            seen.add(value);
            return true;
        });
}

function Message({ message, gameId, onSuggestionClick, closeSignal }: MessageProps) {
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);

    useEffect(() => {
        setShowSuggestions(false);
    }, [closeSignal]);

    const handleGetSuggestions = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (!gameId || isLoadingSuggestions) return;
        if (showSuggestions) {
            setShowSuggestions(false);
            return;
        }

        setShowSuggestions(true);
        if (suggestions.length > 0) return;

        setIsLoadingSuggestions(true);

        try {
            setSuggestions(uniqueSuggestions(await getSuggestedResponses(gameId, 3)));
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
                className={`p-4 rounded-lg w-fit max-w-full sm:max-w-lg relative ${
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
                    <div className="mt-3 flex justify-end">
                        <button
                            onClick={handleGetSuggestions}
                            className="inline-flex items-center gap-1.5 rounded-md bg-neutral-600/40 px-2.5 py-1.5 text-xs text-neutral-200 transition-colors duration-200 hover:bg-neutral-600/70"
                            title={showSuggestions ? "Close response suggestions" : "Open response suggestions"}
                            aria-expanded={showSuggestions}
                        >
                            <Sparkles size={14} className="shrink-0 text-neutral-300" />
                            <span>Suggestions</span>
                        </button>
                    </div>
                )}
            </div>

            {showSuggestions && isGamemasterMessage && (
                <div className="mt-2 grid w-full max-w-full gap-2 overflow-hidden transition-all duration-200 sm:max-w-lg">
                    {isLoadingSuggestions ? (
                        <div className="rounded-lg border border-neutral-700/50 bg-neutral-800/90 p-3 text-neutral-300 shadow-lg backdrop-blur-sm">
                            <p className="text-xs">Generating suggestions...</p>
                        </div>
                    ) : suggestions.length > 0 ? (
                        suggestions.map((suggestion) => (
                            <button
                                key={suggestion}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="rounded-lg border border-neutral-700/50 bg-neutral-800/90 p-3 text-left text-sm text-neutral-200 shadow-lg backdrop-blur-sm transition-colors duration-200 hover:border-neutral-600/50 hover:bg-neutral-700/90"
                            >
                                <span className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-indigo-200/80">
                                    <Sparkles size={12} />
                                    Suggested reply
                                </span>
                                <span className="block break-words">{suggestion}</span>
                            </button>
                        ))
                    ) : (
                        <div className="rounded-lg border border-neutral-700/50 bg-neutral-800/90 p-3 text-neutral-400 shadow-lg backdrop-blur-sm">
                            <p className="text-xs">No suggestions available</p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default Message;
