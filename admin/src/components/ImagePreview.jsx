import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Inline image resize editor — PowerPoint-style drag handles.
 * Renders INSIDE the parent container (not as a modal).
 * Props: src, onClose, onSave
 */
export default function ImagePreview({ src, onClose, onSave }) {
  const [size, setSize] = useState(null);
  const [resizing, setResizing] = useState(null);
  const [startPos, setStartPos] = useState(null);
  const [startSize, setStartSize] = useState(null);
  const imgRef = useRef(null);
  const containerRef = useRef(null);

  const imgSrc = src.startsWith('data:') ? src : (src.startsWith('/') ? src : `/media/${src}`);

  // Fit image into container on first load
  const handleImageLoad = () => {
    if (size) return;
    const img = imgRef.current;
    const container = containerRef.current;
    if (!img || !container) return;
    const maxW = container.clientWidth - 16;
    const maxH = container.clientHeight - 50;
    const ratio = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1);
    setSize({
      width: Math.round(img.naturalWidth * ratio),
      height: Math.round(img.naturalHeight * ratio),
    });
  };

  // Escape = close
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // 8 resize handles (corners + sides)
  const handles = [
    { pos: 'nw', cursor: 'nwse-resize', style: { top: -5, left: -5 } },
    { pos: 'n',  cursor: 'ns-resize',   style: { top: -5, left: '50%', transform: 'translateX(-50%)' } },
    { pos: 'ne', cursor: 'nesw-resize', style: { top: -5, right: -5 } },
    { pos: 'e',  cursor: 'ew-resize',   style: { top: '50%', right: -5, transform: 'translateY(-50%)' } },
    { pos: 'se', cursor: 'nwse-resize', style: { bottom: -5, right: -5 } },
    { pos: 's',  cursor: 'ns-resize',   style: { bottom: -5, left: '50%', transform: 'translateX(-50%)' } },
    { pos: 'sw', cursor: 'nesw-resize', style: { bottom: -5, left: -5 } },
    { pos: 'w',  cursor: 'ew-resize',   style: { top: '50%', left: -5, transform: 'translateY(-50%)' } },
  ];

  const handleMouseDown = (e, handle) => {
    e.preventDefault();
    e.stopPropagation();
    setResizing(handle);
    setStartPos({ x: e.clientX, y: e.clientY });
    setStartSize({ ...size });
  };

  const handleMouseMove = useCallback((e) => {
    if (!resizing || !startPos || !startSize) return;
    const dx = e.clientX - startPos.x;
    const dy = e.clientY - startPos.y;
    let newW = startSize.width;
    let newH = startSize.height;

    if (resizing.includes('e')) newW = Math.max(40, startSize.width + dx);
    if (resizing.includes('w')) newW = Math.max(40, startSize.width - dx);
    if (resizing.includes('s')) newH = Math.max(40, startSize.height + dy);
    if (resizing.includes('n')) newH = Math.max(40, startSize.height - dy);

    setSize({ width: Math.round(newW), height: Math.round(newH) });
  }, [resizing, startPos, startSize]);

  const handleMouseUp = useCallback(() => {
    setResizing(null);
    setStartPos(null);
    setStartSize(null);
  }, []);

  useEffect(() => {
    if (resizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [resizing, handleMouseMove, handleMouseUp]);

  // Save at exact displayed pixel size
  const handleSave = () => {
    if (!imgRef.current || !onSave || !size) return;
    const canvas = document.createElement('canvas');
    canvas.width = size.width;
    canvas.height = size.height;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size.width, size.height);
    ctx.drawImage(imgRef.current, 0, 0, size.width, size.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    onSave(dataUrl);
    onClose();
  };

  // Reset to fit container
  const handleReset = () => {
    const img = imgRef.current;
    const container = containerRef.current;
    if (!img || !container) return;
    const maxW = container.clientWidth - 16;
    const maxH = container.clientHeight - 50;
    const ratio = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1);
    setSize({
      width: Math.round(img.naturalWidth * ratio),
      height: Math.round(img.naturalHeight * ratio),
    });
  };

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex flex-col items-center justify-center overflow-hidden"
      style={{ background: '#1a1a2e', position: 'relative' }}
    >
      {/* ── Controls ── */}
      <div className="flex items-center gap-2 py-1.5 px-2 z-10"
        style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '6px', marginBottom: '6px' }}>
        {size && (
          <span className="text-white text-xs font-mono px-2 py-0.5 rounded"
            style={{ background: 'rgba(59,130,246,0.25)', border: '1px solid rgba(59,130,246,0.4)' }}>
            {size.width} × {size.height} px
          </span>
        )}
        <button onClick={handleReset}
          className="px-2 py-0.5 rounded text-slate-300 text-xs cursor-pointer hover:text-white"
          style={{ background: 'rgba(255,255,255,0.1)' }}>
          ↺ Reset
        </button>
        {onSave && (
          <button onClick={handleSave}
            className="px-2 py-0.5 rounded text-green-300 text-xs cursor-pointer hover:text-green-100"
            style={{ background: 'rgba(34,197,94,0.2)', border: '1px solid rgba(34,197,94,0.35)' }}>
            💾 Saqlash
          </button>
        )}
        <button onClick={onClose}
          className="px-2 py-0.5 rounded text-red-300 text-xs cursor-pointer hover:text-red-100"
          style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)' }}>
          ✕ Bekor
        </button>
      </div>

      {/* ── Image with resize handles ── */}
      {size ? (
        <div className="relative inline-block" style={{ width: size.width, height: size.height }}>
          <img
            ref={imgRef}
            src={imgSrc}
            alt="Edit"
            style={{
              width: size.width,
              height: size.height,
              display: 'block',
              userSelect: 'none',
            }}
            onLoad={handleImageLoad}
            onError={(e) => { e.target.src = '/default_image.jpg'; }}
            draggable={false}
          />
          {/* Dashed selection border */}
          <div className="absolute inset-0 pointer-events-none"
            style={{ border: '2px dashed rgba(59,130,246,0.7)' }} />

          {/* 8 resize handles */}
          {handles.map(h => (
            <div
              key={h.pos}
              className="absolute bg-white border-2 border-blue-500 rounded-sm"
              style={{
                ...h.style,
                width: 10,
                height: 10,
                cursor: h.cursor,
                zIndex: 10,
              }}
              onMouseDown={e => handleMouseDown(e, h.pos)}
            />
          ))}
        </div>
      ) : (
        /* Hidden preloader to get natural dimensions */
        <img
          ref={imgRef}
          src={imgSrc}
          alt="Loading"
          style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
          onLoad={handleImageLoad}
          onError={(e) => { e.target.src = '/default_image.jpg'; }}
        />
      )}

      {/* Hint */}
      <div className="text-slate-500 text-[10px] mt-1 select-none">
        Burchaklardan yoki tomonlardan tortib o'lchamni o'zgartiring
      </div>
    </div>
  );
}
