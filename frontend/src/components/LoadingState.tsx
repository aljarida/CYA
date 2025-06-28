import { useEffect, useState } from 'react';
import { CheckCircle } from 'lucide-react';

const loading_phrases = [
  "Loading your adventure...",
  "Painting the landscape...",
  "Envisioning your portrait...",
  "Consulting the stars...",
  "Charting your destiny...",
  "Encoding your essence...",
  "Composing light from latent space...",
  "Embedding your past into memory...",
  "Sampling visions from the void...",
  "Conditioning the dream engine...",
  "Inferring the laws of your world...",
  "Interpolating between possibilities...",
  "Awaiting convergence on your reality..."
];

function LoadingState() {
  const [index, setIndex] = useState<number>(0);

  useEffect(() => {
    const interval = setInterval(() => {
     setIndex(() => Math.floor(Math.random() * loading_phrases.length));
    }, 5000); 
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-64">
      <div className="text-green-400 animate-pulse">
        <CheckCircle size={80} strokeWidth={1.5} />
      </div>
      <p className="mt-6 text-neutral-200 text-lg font-medium">
        {loading_phrases[index]}
      </p>
    </div>
  );
}

export default LoadingState;
