import { useEffect, useState } from 'react';

function WorldBackdrop({ src }: { src: string }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (src) {
      const img = new Image();
      img.src = src;
      img.onload = () => setLoaded(true);
    }
  }, [src]);

  return (
    <div className="absolute inset-0 w-full h-full z-0 overflow-hidden pointer-events-none">
      <div
        className={`w-full h-full bg-cover bg-top transition-opacity duration-1000 ease-in ${
          loaded ? 'opacity-100' : 'opacity-0'
        }`}
        style={{ backgroundImage: `url(${src})` }}
      >
        <div className="w-full h-full bg-gradient-to-b from-black/0 via-neutral-800/90 to-neutral-900" />
      </div>
    </div>
  );
}

export default WorldBackdrop;
