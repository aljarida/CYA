import { ArrowLeft } from 'lucide-react';
import type { BackButtonProps } from '../misc/types';


function BackButton({ unloadGame }: BackButtonProps) {
  return (
    <button
      onClick={() => unloadGame()}
      className="absolute top-4 left-16 z-10 p-2 rounded-full bg-black/20 hover:bg-black/40 transition-colors duration-200 backdrop-blur-sm"
    >
      <ArrowLeft size={16} className="text-white/70 hover:text-white" />
    </button>
  );
}

export default BackButton;