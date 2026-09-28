import { useState, useEffect } from 'react';
import { MdKeyboardDoubleArrowLeft, MdKeyboardDoubleArrowRight } from 'react-icons/md';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useData } from '../context/DataContext';
import QuestionPickerModal from '../components/QuestionPickerModal';
import { mediaUrl } from '../services/api';

// ─── Sortable Blits Question Number (drag to reorder) ───
function SortableBlitsNum({ id, index, isActive, onClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition: transition || 'all 0.3s',
    background: isActive ? '#608269' : isDragging ? '#4a6a55' : '#343835',
    cursor: 'grab',
    width: '2.25rem',
    padding: '0.5rem 0',
    borderRadius: '0.125rem',
    fontSize: '13px',
    height: '2.5rem',
    color: 'white',
    textAlign: 'center',
    opacity: isDragging ? 0.7 : 1,
    zIndex: isDragging ? 100 : 'auto',
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}
      className="shrink-0"
      onClick={(e) => { e.stopPropagation(); onClick(); }}>
      {index + 1}
    </div>
  );
}

export default function BlitsPage() {
  const {
    blits, sections, lessons, questions,
    updateBlits, addBlits, deleteBlits,
    getQuestionById, getAnswersByQuestion,
    getVal, t, lang,
  } = useData();

  const blitsList = Array.isArray(blits) ? blits : [];
  const [selectedBlitsId, setSelectedBlitsId] = useState(blitsList[0]?.id || null);
  const [editingNameId, setEditingNameId] = useState(null);
  const [editName, setEditName] = useState({});
  const [showPicker, setShowPicker] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!selectedBlitsId && blitsList.length > 0) {
      setSelectedBlitsId(blitsList[0].id);
    }
  }, [blitsList, selectedBlitsId]);

  const selectedBlits = blitsList.find(b => b.id === selectedBlitsId);

  // Blits items ichidagi savollarni olish
  const blitsQuestions = selectedBlits && selectedBlits.items
    ? selectedBlits.items.map(i => getQuestionById(i.question)).filter(Boolean)
    : [];

  const currentQ = blitsQuestions[activeIndex];
  const currentAnswers = currentQ ? getAnswersByQuestion(currentQ.id) : [];

  // Indeksni yangilash
  useEffect(() => {
    setActiveIndex(0);
  }, [selectedBlitsId]);

  useEffect(() => {
    if (activeIndex >= blitsQuestions.length && blitsQuestions.length > 0) {
      setActiveIndex(blitsQuestions.length - 1);
    }
  }, [blitsQuestions.length]);

  // Klaviatura
  useEffect(() => {
    const handleKey = (e) => {
      if (editingNameId) return;
      if (e.key === 'ArrowRight') setActiveIndex(i => i < blitsQuestions.length - 1 ? i + 1 : 0);
      if (e.key === 'ArrowLeft') setActiveIndex(i => i > 0 ? i - 1 : blitsQuestions.length - 1);
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [editingNameId, blitsQuestions.length]);

  const getQuestionMeta = (q) => {
    const lesson = lessons.find(l => l.id === q.lesson);
    const section = lesson ? sections.find(s => s.id === lesson.section) : null;
    return { section, lesson };
  };

  const startEditName = (b) => {
    setEditingNameId(b.id);
    setEditName({ name_uz: b.name_uz, name_ru: b.name_ru, name_cry: b.name_cry });
  };
  const saveEditName = async () => {
    if (editingNameId) {
      await updateBlits(editingNameId, editName);
      setEditingNameId(null);
    }
  };

  const meta = currentQ ? getQuestionMeta(currentQ) : {};

  // Drag-and-drop
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !selectedBlits || !selectedBlits.items) return;

    const items = [...selectedBlits.items];
    const oldIdx = items.findIndex(i => i.question === active.id);
    const newIdx = items.findIndex(i => i.question === over.id);
    if (oldIdx === -1 || newIdx === -1) return;

    const newItems = arrayMove(items, oldIdx, newIdx);
    const itemIds = newItems.map(i => i.id);

    try {
      const { postJSON } = await import('../services/api');
      await postJSON('/manage/blits-questions/reorder/', { ids: itemIds });
      await updateBlits(selectedBlits.id, { items: newItems });
    } catch (err) {
      console.error('Blits reorder error:', err);
    }

    if (activeIndex === oldIdx) setActiveIndex(newIdx);
    else if (oldIdx < activeIndex && newIdx >= activeIndex) setActiveIndex(activeIndex - 1);
    else if (oldIdx > activeIndex && newIdx <= activeIndex) setActiveIndex(activeIndex + 1);
  };

  return (
    <div className="flex h-full">
      {/* ───── Yon panel ───── */}
      <div className="w-56 shrink-0 flex flex-col gap-1.5 py-5 px-3 overflow-y-auto"
        style={{ borderRight: '1px solid rgba(100,140,220,0.12)', background: 'rgba(10,18,40,0.3)' }}>
        <div className="text-[11px] text-slate-500 uppercase tracking-wider mb-2 px-2">⚡ {t('blits')}</div>
        {blitsList.map(b => (
          <div key={b.id}
            className={`flex items-center px-3 py-2.5 rounded-md cursor-pointer transition-all gap-2 group`}
            style={{
              background: b.id === selectedBlitsId ? 'rgba(30,60,140,0.55)' : 'transparent',
              border: `1px solid ${b.id === selectedBlitsId ? '#3b82f6' : 'transparent'}`,
            }}
            onClick={() => setSelectedBlitsId(b.id)}>
            {editingNameId === b.id ? (
              <>
                <input value={editName[`name_${lang}`] || ''}
                  onChange={e => setEditName(prev => ({ ...prev, [`name_${lang}`]: e.target.value }))}
                  onClick={e => e.stopPropagation()}
                  onKeyDown={e => { if (e.key === 'Enter') saveEditName(); if (e.key === 'Escape') setEditingNameId(null); }}
                  autoFocus
                  className="flex-1 min-w-0 bg-black/30 border border-blue-500 text-white px-2 py-0.5 rounded text-sm outline-none" />
                <span className="text-green-400 cursor-pointer text-sm shrink-0" onClick={(e) => { e.stopPropagation(); saveEditName(); }}>💾</span>
                <span className="text-red-400 cursor-pointer text-sm shrink-0"
                  onClick={e => { e.stopPropagation(); if(confirm("O'chirish?")) { deleteBlits(b.id); setEditingNameId(null); if(b.id === selectedBlitsId) setSelectedBlitsId(blits.find(x => x.id !== b.id)?.id || null); } }}>🗑️</span>
              </>
            ) : (
              <>
                <span className="flex-1 text-sm truncate min-w-0">{getVal(b, 'name')}</span>
                <span className="text-[10px] text-slate-500 shrink-0">{(b.items || []).length}</span>
                <span className="text-blue-400 cursor-pointer text-sm shrink-0"
                  onClick={e => { e.stopPropagation(); startEditName(b); }}>✏️</span>
                <span className="text-red-400 cursor-pointer text-sm shrink-0"
                  onClick={e => { e.stopPropagation(); if(confirm("O'chirish?")) { deleteBlits(b.id); if(b.id === selectedBlitsId) setSelectedBlitsId(blits.find(x => x.id !== b.id)?.id || null); } }}>🗑️</span>
              </>
            )}
          </div>
        ))}
        <button onClick={async () => { const nb = await addBlits(); if (nb) setSelectedBlitsId(nb.id); }}
          className="flex items-center justify-center gap-1 rounded-md px-3 py-2 cursor-pointer text-blue-400 text-xs mt-1"
          style={{ border: '2px dashed rgba(100,140,220,0.25)', background: 'transparent' }}>
          ＋ {t('addBlits')}
        </button>
      </div>

      {/* ───── Asosiy kontent ───── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedBlits ? (
          blitsQuestions.length > 0 && currentQ ? (
            <div className="flex flex-col items-center px-6 py-4 pb-20 overflow-y-auto flex-1">
              <div className="w-full max-w-[1100px]">

                {/* Sarlavha */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-2 gap-2">
                  <div className="text-sm">
                    <span className="text-amber-400 font-medium">⚡ {getVal(selectedBlits, 'name')}</span>
                    <span className="text-slate-600 mx-2">|</span>
                    <span className="text-red-400 text-xs">
                      {meta.section && getVal(meta.section, 'name')} › {meta.lesson && getVal(meta.lesson, 'name')}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 items-center">
                    <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                      currentQ.is_in_web
                        ? 'text-green-300 border border-green-500/30'
                        : 'text-red-300 border border-red-500/20'
                    }`} style={{ background: currentQ.is_in_web ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.15)' }}>
                      {currentQ.is_in_web ? '✓ Web' : '✕ Web'}
                    </span>
                    <button onClick={() => setShowPicker(true)}
                      className="px-3 py-1.5 text-xs cursor-pointer rounded flex items-center gap-1"
                      style={{ background: 'rgba(59,130,246,0.2)', border: '1px solid rgba(59,130,246,0.4)', color: '#60a5fa' }}>
                      ✏️ <span className="hidden sm:inline">{t('selectQuestions')}</span><span className="sm:hidden">Tanlash</span>
                    </button>
                  </div>
                </div>

                {/* Savol matni */}
                <div className="rounded mb-3 py-2.5 px-4 text-center text-base font-semibold"
                  style={{ background: 'rgba(30,58,138,0.4)', fontSize: '19px' }}>
                  {getVal(currentQ, 'text')}
                </div>

                {/* Javoblar + rasm */}
                <div className="flex gap-5 min-h-[300px]">
                  {/* Javoblar */}
                  <div className="flex flex-col gap-2 w-[380px] shrink-0">
                    {currentAnswers.map((answer, idx) => (
                      <div key={answer.id} className="flex items-center border border-white/10 rounded-sm overflow-hidden">
                        <span className="w-10 min-h-[38px] flex items-center justify-center text-xs font-bold text-white shrink-0"
                          style={{ background: answer.is_true ? '#22c55e' : '#3b82f6' }}>
                          F{idx + 1}
                        </span>
                        <span className="flex-1 py-2 px-3 text-sm"
                          style={{ color: '#c8d6e5', background: 'rgba(30,58,138,0.3)', borderLeft: '1px solid rgba(0,0,0,0.3)' }}>
                          {getVal(answer, 'text')}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Rasm */}
                  <div className="flex-1 bg-white rounded flex items-center justify-center min-h-[300px] overflow-hidden">
                    {currentQ.image ? (
                      currentQ.image.startsWith('data:') ? (
                        <img src={currentQ.image} alt="Savol" className="max-w-full max-h-[400px] object-contain" />
                      ) : (
                        <img src={mediaUrl(currentQ.image)} alt="Savol" className="max-w-full max-h-[400px] object-contain"
                          onError={(e) => { e.target.src = mediaUrl('default_image.jpg'); }} />
                      )
                    ) : (
                      <img src={mediaUrl('default_image.jpg')} alt="Default" className="max-w-full max-h-[400px] object-contain" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <div className="text-6xl opacity-30">⚡</div>
              <p className="text-slate-500 text-sm">{getVal(selectedBlits, 'name')} — savollar yo'q</p>
              <button onClick={() => setShowPicker(true)}
                className="px-5 py-2.5 rounded text-blue-400 cursor-pointer text-sm"
                style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}>
                ＋ {t('selectQuestions')}
              </button>
            </div>
          )
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-600 text-sm">
            Blitsni tanlang
          </div>
        )}

        {/* Paginatsiya */}
        {selectedBlits && blitsQuestions.length > 0 && (
          <div className="flex items-center gap-1.5 px-4 py-2.5 justify-center shrink-0"
            style={{ background: 'rgba(10,14,26,0.9)', backdropFilter: 'blur(10px)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <button onClick={() => setActiveIndex(i => i > 0 ? i - 1 : blitsQuestions.length - 1)}
              className="px-3 py-2 rounded text-white cursor-pointer" style={{ background: 'rgba(100,116,139,0.3)' }}>
              <MdKeyboardDoubleArrowLeft size={20} />
            </button>

            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={blitsQuestions.map(q => q.id)}>
                <div className="flex flex-wrap gap-1 items-center justify-center max-w-[80vw] overflow-x-auto">
                  {blitsQuestions.map((q, idx) => (
                    <SortableBlitsNum key={q.id} id={q.id} index={idx}
                      isActive={idx === activeIndex}
                      onClick={() => setActiveIndex(idx)} />
                  ))}
                </div>
              </SortableContext>
            </DndContext>

            <button onClick={() => setActiveIndex(i => i < blitsQuestions.length - 1 ? i + 1 : 0)}
              className="px-3 py-2 rounded text-white cursor-pointer" style={{ background: 'rgba(100,116,139,0.3)' }}>
              <MdKeyboardDoubleArrowRight size={20} />
            </button>
          </div>
        )}
      </div>

      {showPicker && selectedBlits && (
        <QuestionPickerModal
          blits={selectedBlits}
          onClose={() => setShowPicker(false)}
        />
      )}
    </div>
  );
}
