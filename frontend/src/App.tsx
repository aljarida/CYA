import { useState, useEffect } from 'react';
import { CheckCircle } from 'lucide-react';

const url = "http://localhost:3000/api/response";

function ChatApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [showModal, setShowModal] = useState(true);
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [playerInfo, setPlayerInfo] = useState({
    playerName: "",
    gameTheme: "",
    characterDescription: "",
    worldDescription: ""
  });

  // Form validation state
  const [isFormValid, setIsFormValid] = useState(false);

  // Effect to check form validity
  useEffect(() => {
    setIsFormValid(playerInfo.playerName.trim() !== "" && playerInfo.gameTheme.trim() !== "");
  }, [playerInfo]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPlayerInfo({
      ...playerInfo,
      [name]: value
    });
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!isFormValid) return;
    
    setFormSubmitted(true);
    
    // After 1.5 seconds, close the modal and add initial system message
    setTimeout(() => {
      setShowModal(false);
      
      // Add welcome message from the system
      const welcomeMessage = `Welcome to your adventure, ${playerInfo.playerName}! 
      \nGame Theme: ${playerInfo.gameTheme}
      ${playerInfo.characterDescription ? `\nYour character: ${playerInfo.characterDescription}` : ''}
      ${playerInfo.worldDescription ? `\nWorld setting: ${playerInfo.worldDescription}` : ''}
      \nLet's begin your journey! What would you like to do?`;
      
      setMessages([{ sender: 'system', content: welcomeMessage }]);
    }, 1500);
  };

  const handleClick = async () => {
    if (!input.trim()) return;
    const newMessages = [...messages, { sender: 'user', content: input }];
    setMessages(newMessages);
    setInput("");
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          content: input,
          playerInfo: playerInfo // Send player info with each request
        })
      });
      const result = await response.json();
      setMessages([...newMessages, { sender: 'system', content: result.content }]);
    } catch (error) {
      console.error("Error:", error);
      setMessages([...newMessages, { sender: 'system', content: "Error fetching message" }]);
    }
  };

  // Handle Enter key in chat input
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleClick();
    }
  };

  return (
    <div className="relative flex flex-col h-screen bg-gradient-to-br from-neutral-800 via-gray-700 to-neutral-600 p-8">
      {/* Setup Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-neutral-800 rounded-xl p-8 shadow-2xl w-full max-w-md relative">
            {formSubmitted ? (
              <div className="flex flex-col items-center justify-center h-64">
                <div className="text-green-400 animate-pulse">
                  <CheckCircle size={80} strokeWidth={1.5} />
                </div>
                <p className="mt-6 text-neutral-200 text-lg font-medium">Adventure is loading...</p>
              </div>
            ) : (
              <>
                <h2 className="text-2xl font-bold text-neutral-200 mb-6">Adventure Setup</h2>
                <form onSubmit={handleFormSubmit}>
                  <div className="space-y-4">
                    <div>
                      <label htmlFor="playerName" className="block text-neutral-300 mb-1">Player Name<span className="text-red-500">*</span></label>
                      <input
                        id="playerName"
                        name="playerName"
                        type="text"
                        value={playerInfo.playerName}
                        onChange={handleInputChange}
                        className="w-full p-3 bg-neutral-700 text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500"
                        placeholder="Enter your name"
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="gameTheme" className="block text-neutral-300 mb-1">Game Theme<span className="text-red-500">*</span></label>
                      <input
                        id="gameTheme"
                        name="gameTheme"
                        type="text"
                        value={playerInfo.gameTheme}
                        onChange={handleInputChange}
                        className="w-full p-3 bg-neutral-700 text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500"
                        placeholder="Fantasy, Sci-fi, Horror, etc."
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="characterDescription" className="block text-neutral-300 mb-1">Description of Player Character (optional)</label>
                      <textarea
                        id="characterDescription"
                        name="characterDescription"
                        value={playerInfo.characterDescription}
                        onChange={handleInputChange}
                        className="w-full p-3 bg-neutral-700 text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 h-20"
                        placeholder="Describe your character"
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="worldDescription" className="block text-neutral-300 mb-1">Description of World (optional)</label>
                      <textarea
                        id="worldDescription"
                        name="worldDescription"
                        value={playerInfo.worldDescription}
                        onChange={handleInputChange}
                        className="w-full p-3 bg-neutral-700 text-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 h-20"
                        placeholder="Describe the game world"
                      />
                    </div>
                    
                    <button
                      type="submit"
                      disabled={!isFormValid}
                      className={`w-full py-3 rounded-lg shadow-lg mt-4 ${
                        isFormValid
                          ? 'bg-green-600 hover:bg-green-700 text-white'
                          : 'bg-neutral-600 text-neutral-400 cursor-not-allowed'
                      }`}
                    >
                      Begin Adventure
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {/* Chat Area */}
      <div className="flex flex-col flex-grow space-y-4 bg-neutral-900/80 rounded-xl p-6 overflow-y-auto shadow-md backdrop-blur-md">
        {messages.map((msg, index) => (
          <div key={index} className={`p-4 rounded-lg w-fit max-w-lg ${
            msg.sender === 'user' 
              ? 'bg-neutral-800/80 text-neutral-200 self-end' 
              : 'bg-neutral-700/80 text-neutral-300 self-start'
            } backdrop-blur-sm shadow-lg`}
          >              
            <p className="text-sm break-words whitespace-pre-line">{msg.content}</p>
          </div>
        ))}
      </div>
      
      {/* Input Area */}
      <div className="flex mt-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="What would you like to do?"
          className="flex-1 p-3 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 shadow-lg"
        />
        <button 
          onClick={handleClick} 
          className="ml-2 px-4 py-2 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm shadow-lg hover:bg-neutral-700"
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatApp;
