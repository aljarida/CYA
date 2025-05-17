import { useState } from 'react';

const url = "http://localhost:3000/api/response";

function ChatApp() {
  const [messages, setMessages] = useState<{sender: 'user' | 'system', content: string}[]>([]);
  const [input, setInput] = useState("");

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
        body: JSON.stringify({ content: input })
      });
      const result = await response.json();
      setMessages([...newMessages, { sender: 'system', content: result.content }]);
    } catch (error) {
      console.error("Error:", error);
      setMessages([...newMessages, { sender: 'system', content: "Error fetching message" }]);
    }
  };

  return (
    <div className="relative flex flex-col h-screen bg-gradient-to-br from-neutral-800 via-gray-700 to-neutral-600 p-8">
      <div className="flex flex-col flex-grow space-y-4 bg-neutral-900/80 rounded-xl p-6 overflow-y-auto shadow-md backdrop-blur-md">
        {messages.map((msg, index) => (
          <div key={index} className={`p-4 rounded-lg w-fit max-w-lg ${msg.sender === 'user' ? 'bg-neutral-800/80 text-neutral-200 self-end' : 'bg-neutral-700/80 text-neutral-300 self-start'} backdrop-blur-sm shadow-lg`}>              
            <p className="text-sm break-words">{msg.content}</p>
          </div>
        ))}
      </div>
      <div className="flex mt-4">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 p-3 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-neutral-500 placeholder-neutral-500 shadow-lg"
        />
        <button onClick={handleClick} className="ml-2 px-4 py-2 bg-neutral-800/80 text-neutral-200 rounded-lg backdrop-blur-sm shadow-lg hover:bg-neutral-700">
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatApp;

