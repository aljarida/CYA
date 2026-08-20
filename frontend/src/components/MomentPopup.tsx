import { useEffect, useState } from 'react';

import type { StoryMoment } from '../misc/types';

type MomentPopupProps = {
  moment: StoryMoment | null;
  onDismiss: () => void;
};

function MomentPopup({ moment, onDismiss }: MomentPopupProps) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    if (!moment) return;

    const img = new Image();
    img.src = moment.imageSrc;
    img.onload = () => setLoaded(true);
  }, [moment]);

  if (!moment) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="max-w-2xl w-full">
        <div className="relative rounded-xl overflow-hidden border border-white/20 shadow-2xl bg-neutral-900">
          {!loaded && (
            <div className="aspect-video w-full flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white/70 animate-spin" />
            </div>
          )}
          <img
            src={moment.imageSrc}
            alt={moment.caption}
            className={`w-full object-cover transition-opacity duration-700 ease-in ${
              loaded ? 'opacity-100' : 'opacity-0 absolute inset-0'
            }`}
          />
          {loaded && (
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
              <p className="text-white text-base font-medium italic text-center">{moment.caption}</p>
            </div>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="mt-4 mx-auto block px-5 py-2 rounded-full bg-white/10 hover:bg-white/20 text-white/80 hover:text-white text-sm transition-colors"
        >
          Continue
        </button>
      </div>
    </div>
  );
}

export default MomentPopup;
