import { useState, useRef, useEffect } from 'react';

function Portrait({ src }: { src: string }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // Close the modal when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setIsModalOpen(false);
      }
    }

    if (isModalOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isModalOpen]);

  if (!src) return null;

  return (
    <>
      <div
        onClick={() => setIsModalOpen(true)}
        className="cursor-pointer absolute top-4 right-8 border-4 w-20 h-20 z-10 rounded-xl backdrop-blur-sm shadow-xl border border-white/20 hover:outline-none hover:ring-2 hover:ring-neutral-500"
      >
        <img
          src={src}
          alt="Player Portrait"
          className="w-full h-full object-cover rounded-lg"
        />
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div ref={modalRef} className="p-4 bg-white/10 rounded-xl shadow-xl border border-white/30 max-w-[90%] max-h-[90%]">
            <img
              src={src}
              alt="Enlarged Portrait"
              className="max-w-full max-h-[80vh] object-contain rounded-xl"
            />
          </div>
        </div>
      )}
    </>
  );
}

export default Portrait;
