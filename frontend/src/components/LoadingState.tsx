import { CheckCircle } from 'lucide-react';

function LoadingState() {
    return (
    <div className="flex flex-col items-center justify-center h-64">
      <div className="text-green-400 animate-pulse">
        <CheckCircle size={80} strokeWidth={1.5} />
      </div>
      <p className="mt-6 text-neutral-200 text-lg font-medium">
        Adventure is loading...
      </p>
    </div>
)};

export default LoadingState;