import { Heart, HeartCrack } from "lucide-react";

function HitPoints({ hitPoints }: { hitPoints: number }) {
  if (hitPoints < 0) return null;

  return (
    <div className="absolute top-26 right-8 flex gap-1 w-20 justify-end">
      {Array.from({ length: 5 }).map((_, i) =>
        i < 5 - hitPoints ? (
          <HeartCrack key={i} className="w-4 h-4 z-3 text-red-400" />
        ) : (
          <Heart key={i} className="w-4 h-4 z-3 text-red-400 fill-current stroke-none" />
        )
      )}
    </div>
  );
}

export default HitPoints;
