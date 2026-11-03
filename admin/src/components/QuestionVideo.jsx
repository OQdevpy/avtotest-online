import { useRef } from 'react';

// Savolning video izohi: ko'rish rejimida player, tahrirda fayl tanlash/o'chirish.
// Vertikal video ham, gorizontal ham o'z nisbatida ko'rinadi — balandlik
// cheklangan, kenglik videoning o'ziga moslashadi (object-contain).
export default function QuestionVideo({ src, editing, pending, onPick, onClear }) {
  const inputRef = useRef(null);

  return (
    <div className="mt-3 p-3 rounded-lg" style={{ background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.3)' }}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-purple-300 font-semibold">🎬 Video izoh</span>
        {editing && (
          <button
            onClick={() => inputRef.current?.click()}
            className="text-xs px-2 py-1 bg-purple-600 text-white rounded cursor-pointer hover:bg-purple-700"
          >
            📁 Video yuklash
          </button>
        )}
      </div>

      {editing && (
        <input
          ref={inputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/webm,.mp4,.m4v,.mov,.webm"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onPick(file);
            e.target.value = '';
          }}
        />
      )}

      {src ? (
        <div className="relative">
          <video
            key={src}
            src={src}
            controls
            playsInline
            preload="metadata"
            className="block mx-auto max-w-full max-h-72 rounded bg-black"
          />
          {pending && (
            <p className="text-xs text-yellow-400 mt-1">⏳ Yangi video tanlandi (saqlashni bosing)</p>
          )}
          {editing && (
            <button
              onClick={onClear}
              title="Videoni olib tashlash"
              className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs cursor-pointer"
            >×</button>
          )}
        </div>
      ) : (
        <p className="text-slate-500 text-xs">
          {editing ? 'Video kiritilmagan (mp4, mov, webm — 300 MB gacha)' : "Video yo'q"}
        </p>
      )}
    </div>
  );
}
