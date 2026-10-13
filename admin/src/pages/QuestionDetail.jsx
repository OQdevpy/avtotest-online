import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useParams, useNavigate, useOutletContext } from 'react-router-dom';
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from 'react-icons/md';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useData } from '../context/DataContext';
import ImagePreview from '../components/ImagePreview';
import { mediaUrl } from '../services/api';

// ─── Sortable savol raqami ───
function SortableQuestionNum({ id, index, isActive, onClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = {
    transform: CSS.Transform.toString(transform),
    background: isActive ? '#608269' : isDragging ? '#4a6a55' : '#343835',
    cursor: 'grab',
    width: '2.25rem',
    padding: '0.5rem 0',
    borderRadius: '0.125rem',
    color: 'white',
    textAlign: 'center',
    height: '2.5rem',
    opacity: isDragging ? 0.7 : 1,
    zIndex: isDragging ? 100 : 'auto',
    transition: transition || 'all 0.3s',
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}
      onClick={(e) => { e.stopPropagation(); onClick(); }}>
      {index + 1}
    </div>
  );
}

// ─── Rasm komponenti ───
// Desktop ilovadagi (frontend/src/components/ImageComponent.jsx) bilan bir xil
// ko'rinish: oq blok, balandligi ekranga qarab 430/500/560px; katta rasm
// blokni to'ldiradi, kichigi (jumladan default logotip) o'z o'lchamida
// markazda turadi.
function QuestionImageComponent({ currentItem, editing, onClickImage, fileInputRef, onImageChange, previewActive, children }) {
  const [containerHeight, setContainerHeight] = useState('560px');
  const [isImageLarge, setIsImageLarge] = useState(false);

  useEffect(() => {
    const updateContainerHeight = () => {
      const vh = window.innerHeight;
      if (vh < 800) setContainerHeight('430px');
      else if (vh < 890) setContainerHeight('500px');
      else setContainerHeight('560px');
    };
    updateContainerHeight();
    window.addEventListener('resize', updateContainerHeight);
    return () => window.removeEventListener('resize', updateContainerHeight);
  }, []);

  const imageSrc = currentItem.image;
  const hasImage = imageSrc && imageSrc.length > 0;
  const resolvedSrc = hasImage
    ? (imageSrc.startsWith('data:') ? imageSrc : mediaUrl(imageSrc))
    : mediaUrl('default_image.jpg');

  const handleLoad = (e) => {
    const { naturalWidth: w, naturalHeight: h } = e.currentTarget;
    // Kichik ekranda blok desktopdagidan pastroq bo'lishi mumkin — haqiqiy balandlik
    const limit = Math.min(parseInt(containerHeight), e.currentTarget.parentElement.clientHeight);
    setIsImageLarge(w > 500 || h > 500 || h > limit || w > limit);
  };

  return (
    <div
      className="group relative w-full flex items-center justify-center bg-white cursor-pointer"
      style={{
        // Desktop balandligi, lekin sahifadagi bo'sh joydan oshmaydi —
        // uzun savol yoki kichik ekranda rasm pastki panel ostiga kirmaydi
        height: `min(${containerHeight}, 100%)`,
        minHeight: '240px',
        boxShadow: '0 0 10px rgba(0, 0, 0, 0.1)',
        background: previewActive ? '#1a1a2e' : '#ffffff',
      }}
      onClick={() => {
        if (previewActive) return;
        if (editing) {
          fileInputRef?.current?.click();
        } else if (hasImage) {
          onClickImage(resolvedSrc);
        }
      }}
      title={editing ? 'Rasmni almashtirish' : hasImage ? 'Kattalashtirib ko\'rish' : undefined}
    >
      {previewActive ? children : (
        <>
          <img
            src={resolvedSrc}
            alt="Savol rasmi"
            className={`${isImageLarge ? 'object-contain' : 'object-none'} w-full`}
            style={{ maxWidth: '100%', maxHeight: '100%' }}
            onLoad={handleLoad}
            onError={(e) => { e.target.src = mediaUrl('default_image.jpg'); }}
          />
          {editing && (
            <span className="absolute bottom-3 right-3 px-3 py-1.5 rounded-md text-xs font-semibold text-white bg-slate-900/80 opacity-0 group-hover:opacity-100 transition-opacity">
              🖼️ {hasImage ? 'Rasmni almashtirish' : 'Rasm yuklash'}
            </span>
          )}
          {editing && (
            <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={onImageChange} />
          )}
        </>
      )}
    </div>
  );
}

export default function QuestionDetail() {
  const { sectionId, lessonId } = useParams();
  const navigate = useNavigate();
  const lid = Number(lessonId);
  const sid = Number(sectionId);
  const {
    sections, lessons, getQuestionsByLesson, getAnswersByQuestion,
    updateQuestion, addQuestion, deleteQuestion, reorderQuestions,
    updateAnswer, addAnswer, deleteAnswer,
    uploadQuestionImage, uploadExplanationImage,
    getVal, t, lang,
  } = useData();

  const section = sections.find(s => s.id === sid);
  const lesson = lessons.find(l => l.id === lid);
  const questionsList = getQuestionsByLesson(lid);

  const [activeIndex, setActiveIndex] = useState(0);
  const [editing, setEditing] = useState(false);
  const [editQ, setEditQ] = useState({});
  const [editAnswers, setEditAnswers] = useState([]);
  const [previewImage, setPreviewImage] = useState(null);
  const [previewDescImage, setPreviewDescImage] = useState(null);
  const [showLessonPicker, setShowLessonPicker] = useState(false);
  // Navbar'dagi joy — "Boshqa mavzu" va "Tahrirlash" tugmalari shu yerga chiqadi
  const { navbarSlot, navbarTitleSlot } = useOutletContext() || {};

  const [pendingImageFile, setPendingImageFile] = useState(null);
  const [pendingImagePreview, setPendingImagePreview] = useState(null);
  const [pendingDescFile, setPendingDescFile] = useState(null);
  const [pendingDescPreview, setPendingDescPreview] = useState(null);
  const fileInputRef = useRef(null);
  const descImageInputRef = useRef(null);

  const currentQ = questionsList[activeIndex];
  const currentAnswers = currentQ ? getAnswersByQuestion(currentQ.id) : [];

  // Savollar o'zgarganda indeksni to'g'rilash
  useEffect(() => {
    if (activeIndex >= questionsList.length && questionsList.length > 0) {
      setActiveIndex(questionsList.length - 1);
    }
  }, [questionsList.length]);

  // Klaviatura bilan harakatlanish
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (editing) return;
      if (event.key === 'ArrowRight') {
        setActiveIndex((prev) => (prev === questionsList.length - 1 ? 0 : prev + 1));
      } else if (event.key === 'ArrowLeft') {
        setActiveIndex((prev) => (prev === 0 ? questionsList.length - 1 : prev - 1));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [editing, activeIndex, questionsList.length]);

  const handlePrev = () => {
    setActiveIndex((prev) => {
      if (questionsList.length === 0) return prev;
      return prev === 0 ? questionsList.length - 1 : prev - 1;
    });
  };

  const handleNext = () => {
    setActiveIndex((prev) => (prev === questionsList.length - 1 ? 0 : prev + 1));
  };

  // Tahrirlashni boshlash
  const startEdit = () => {
    if (!currentQ) return;
    setEditQ({
      text_uz: currentQ.text_uz,
      text_ru: currentQ.text_ru,
      text_cry: currentQ.text_cry,
      explanation_uz: currentQ.explanation_uz || '',
      explanation_ru: currentQ.explanation_ru || '',
      explanation_cry: currentQ.explanation_cry || '',
      image: currentQ.image,
      explanation_image: currentQ.explanation_image || '',
      is_in_web: currentQ.is_in_web,
      is_published: currentQ.is_published,
    });
    setEditAnswers(currentAnswers.map(a => ({ ...a })));
    setPendingImageFile(null);
    setPendingImagePreview(null);
    setPendingDescFile(null);
    setPendingDescPreview(null);
    setEditing(true);
  };

  // Tahrirlashni saqlash
  const saveEdit = async () => {
    if (!currentQ) return;

    const questionUpdate = {
      text_uz: editQ.text_uz,
      text_ru: editQ.text_ru,
      text_cry: editQ.text_cry,
      explanation_uz: editQ.explanation_uz,
      explanation_ru: editQ.explanation_ru,
      explanation_cry: editQ.explanation_cry,
      is_in_web: editQ.is_in_web,
      is_published: editQ.is_published,
    };
    await updateQuestion(currentQ.id, questionUpdate);

    // Asosiy rasm yuklash
    if (pendingImageFile && uploadQuestionImage) {
      await uploadQuestionImage(currentQ.id, pendingImageFile);
    }

    // Izoh rasmi yuklash
    if (pendingDescFile && uploadExplanationImage) {
      await uploadExplanationImage(currentQ.id, pendingDescFile);
    }

    // Javoblarni yangilash
    for (const a of editAnswers) {
      // Yangi javob ham serverda bo'sh holda yaratilgan — matnini yozib qo'yamiz
      await updateAnswer(a.id, {
        text_uz: a.text_uz, text_ru: a.text_ru, text_cry: a.text_cry, is_true: a.is_true,
      });
    }

    setPendingImageFile(null);
    setPendingImagePreview(null);
    setPendingDescFile(null);
    setPendingDescPreview(null);
    setEditing(false);
  };

  // Yangi savol qo'shish
  const handleAddQuestion = () => {
    addQuestion(lid);
    setActiveIndex(questionsList.length);
  };

  // Drag-and-drop tartiblash
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const ids = questionsList.map(q => q.id);
    const oldIdx = ids.indexOf(active.id);
    const newIdx = ids.indexOf(over.id);
    const newIds = arrayMove(ids, oldIdx, newIdx);
    reorderQuestions(lid, newIds);
    if (activeIndex === oldIdx) setActiveIndex(newIdx);
    else if (oldIdx < activeIndex && newIdx >= activeIndex) setActiveIndex(activeIndex - 1);
    else if (oldIdx > activeIndex && newIdx <= activeIndex) setActiveIndex(activeIndex + 1);
  };

  // Asosiy rasm tanlash
  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingImageFile(file);
    const url = URL.createObjectURL(file);
    setPendingImagePreview(url);
  };

  // Izoh rasmi tanlash
  const handleDescImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingDescFile(file);
    const url = URL.createObjectURL(file);
    setPendingDescPreview(url);
  };

  // Izoh rasmi manbai
  const getDescImageSrc = (question, isPendingAvailable) => {
    if (isPendingAvailable) return pendingDescPreview;
    const value = question?.explanation_image;
    if (!value) return null;
    return mediaUrl(value);
  };

  // Savolni boshqa darsga ko'chirish
  const handleMoveToLesson = async (newLessonId) => {
    if (!currentQ || newLessonId === lid) return;
    await updateQuestion(currentQ.id, { lesson: newLessonId });
    setShowLessonPicker(false);
    const newLesson = lessons.find(l => l.id === newLessonId);
    if (newLesson) {
      navigate(`/sections/${newLesson.section}/lessons/${newLessonId}/questions`);
    }
  };

  if (questionsList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-slate-400 text-lg">{t('questions')}: 0</p>
        <button onClick={handleAddQuestion}
          className="px-6 py-3 rounded text-blue-400 cursor-pointer text-sm"
          style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}>
          ＋ {t('addQuestion')}
        </button>
      </div>
    );
  }

  if (!currentQ) return null;

  // O'ng paneldagi katta rasm — doim savol rasmi. Izoh rasmi faqat chap
  // pastdagi kichik blokda ko'rsatiladi/kattalashtiriladi (dublikat olib
  // tashlandi).
  const displayedImageSrc = editing ? (pendingImagePreview || editQ.image) : currentQ.image;

  const displayAnswers = editing ? editAnswers : currentAnswers;
  const imageItem = { image: displayedImageSrc || '' };

  return (
    <div className="md:h-full flex flex-col">
    <div className="flex-1 md:min-h-0 flex flex-col gap-5 px-6 md:px-10 pt-4 pb-4">
      {/* ─── Sarlavha qatori ─── */}
      <div className="flex flex-col gap-0.5">
        {navbarTitleSlot && lesson && createPortal(
          <h2 className="text-lg font-bold text-red-100 truncate" title={getVal(lesson, 'name')}>
            {getVal(lesson, 'name')}
          </h2>,
          navbarTitleSlot,
        )}

        {navbarSlot && createPortal(
          editing ? (
            <>
              <button onClick={() => { if(confirm("O'chirish?")) { deleteQuestion(currentQ.id); setEditing(false); } }}
                className="px-4 py-1.5 text-sm font-semibold text-white flex items-center gap-1.5 border border-red-900 bg-red-950/60 cursor-pointer hover:bg-red-950/80">
                🗑️ {t('delete')}
              </button>
              <button onClick={saveEdit}
                className="px-4 py-1.5 text-sm font-semibold text-white flex items-center gap-1.5 border border-green-900 bg-green-950/60 cursor-pointer hover:bg-green-950/80">
                💾 {t('save')}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setShowLessonPicker(true)}
                className="px-4 py-1.5 text-sm font-semibold text-orange-300 border border-orange-500/30 cursor-pointer hover:bg-orange-500/20"
                style={{ background: 'rgba(249,115,22,0.15)' }}
              >
                📁 Boshqa mavzu
              </button>
              <button
                onClick={startEdit}
                className="px-4 py-1.5 text-sm font-semibold text-white flex items-center gap-1.5 border border-blue-900 bg-blue-950/60 cursor-pointer hover:bg-blue-900/60"
              >
                ✏️ {t('edit')}
              </button>
            </>
          ),
          navbarSlot,
        )}

        {/* ─── Savol matni ─── */}
        {editing ? (
          <div className="font-bold text-white bg-blue-900/30 rounded-lg p-2 flex justify-center items-center"
            style={{ fontSize: '19px' }}>
            <textarea value={editQ[`text_${lang}`] || ''}
              onChange={e => setEditQ(prev => ({ ...prev, [`text_${lang}`]: e.target.value }))}
              rows={2}
              className="w-full bg-transparent border border-blue-500 rounded-md text-white text-center font-bold resize-none outline-none px-3 py-2"
              // Uzun savol to'liq ko'rinsin — maydon matnga qarab o'sadi
              style={{ fontSize: '19px', fieldSizing: 'content', maxHeight: '30vh' }} />
          </div>
        ) : (
          <h2 className="font-bold text-white bg-blue-900/30 rounded-lg px-4 py-3 text-center leading-snug"
            style={{ fontSize: '19px' }}>
            {getVal(currentQ, 'text')}
          </h2>
        )}
      </div>

      {/* ─── Asosiy qism: javoblar + rasm (qolgan balandlikni egallaydi) ─── */}
      <div className="md:flex-1 md:min-h-0">
        <div className="grid grid-cols-1 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:grid-rows-[minmax(0,1fr)] md:h-full gap-6 md:gap-10 items-start">
          {/* Javoblar ustuni */}
          <div className="flex flex-col gap-2 min-w-0 md:max-h-full md:overflow-y-auto md:pr-1">
            {displayAnswers.map((answer, index) => (
              <div
                key={answer.id}
                className="mb-2 flex items-center border border-gray-400"
              >
                {editing ? (
                  <>
                    <span
                      className="flex items-center justify-center"
                      style={{
                        height: '100%',
                        width: '3rem',
                        minHeight: '38px',
                        backgroundColor: answer.is_true ? '#32a852' : 'blue',
                        color: '#fff',
                        cursor: 'pointer',
                        flexShrink: 0,
                      }}
                      onClick={() => {
                        setEditAnswers(prev => prev.map(a => a.id === answer.id ? { ...a, is_true: !a.is_true } : a));
                      }}
                    >
                      {answer.is_true ? '✓' : 'F' + (index + 1)}
                    </span>
                    <input type="text" value={answer[`text_${lang}`] || ''}
                      onChange={e => {
                        const val = e.target.value;
                        setEditAnswers(prev => prev.map(a => a.id === answer.id ? { ...a, [`text_${lang}`]: val } : a));
                      }}
                      className="p-1 rounded-sm text-white bg-blue-950/40 min-h-full outline-none"
                      style={{ border: '1px solid #000', fontSize: '17px', width: '100%' }}
                    />
                    <span className="text-red-400 cursor-pointer px-2 text-sm flex-shrink-0"
                      onClick={() => {
                        deleteAnswer(answer.id);
                        setEditAnswers(prev => prev.filter(a => a.id !== answer.id));
                      }}>🗑️</span>
                  </>
                ) : (
                  <>
                    <span
                      className="flex items-center justify-center"
                      style={{
                        height: '100%',
                        width: '3rem',
                        minHeight: '38px',
                        backgroundColor: answer.is_true ? '#32a852' : 'blue',
                        justifyContent: 'center',
                        alignItems: 'center',
                        color: '#fff',
                        flexShrink: 0,
                      }}
                    >
                      F{index + 1}
                    </span>
                    <h2
                      className="p-1 rounded-sm border-blue-900 text-white bg-blue-950/40 min-h-full"
                      style={{ border: '1px solid #000', fontSize: '17px', width: '100%' }}
                    >
                      {getVal(answer, 'text')}
                    </h2>
                  </>
                )}
              </div>
            ))}
            {editing && (
              <button onClick={async () => {
                const newA = await addAnswer(currentQ.id);
                if (newA) setEditAnswers(prev => [...prev, { ...newA, _new: true }]);
              }}
                className="flex items-center justify-center gap-1 rounded-md px-4 py-2 mt-1 cursor-pointer text-blue-400 text-xs"
                style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}>
                ＋ {t('addAnswer')}
              </button>
            )}

            {/* Izoh matni (O'qish yoki tahrirlash) */}
            {editing ? (
              <div className="mt-3 p-3 rounded-lg bg-blue-950/30 border border-blue-800/40">
                <div className="text-xs font-semibold text-amber-300 mb-1">💡 Izoh matni ({lang.toUpperCase()}):</div>
                <textarea
                  value={editQ[`explanation_${lang}`] || ''}
                  onChange={e => setEditQ(prev => ({ ...prev, [`explanation_${lang}`]: e.target.value }))}
                  rows={3}
                  placeholder="Savol bo'yicha tushuntirish / izoh matni..."
                  className="w-full bg-slate-900 border border-blue-500/50 rounded p-2 text-white text-xs outline-none"
                />
              </div>
            ) : (
              getVal(currentQ, 'explanation') && (
                <div className="mt-3 p-3 rounded-lg bg-amber-950/20 border border-amber-500/30">
                  <div className="text-xs font-semibold text-amber-400 mb-1 flex items-center gap-1">
                    💡 Izoh matni:
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                    {getVal(currentQ, 'explanation')}
                  </p>
                </div>
              )
            )}

            {/* Izoh rasmi bo'limi */}
            <div className="mt-3 p-3 rounded-lg" style={{ background: 'rgba(100,140,220,0.1)', border: '1px solid rgba(100,140,220,0.3)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-blue-300 font-semibold">📝 Izoh rasmi</span>
                {editing && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => descImageInputRef.current?.click()}
                      className="text-xs px-2 py-1 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700"
                    >
                      📁 Fayldan yuklash
                    </button>
                  </div>
                )}
              </div>

              {editing ? (
                <div className="mb-2">
                  <input
                    ref={descImageInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleDescImageChange}
                  />
                  {(pendingDescPreview || editQ.explanation_image) ? (() => {
                    const displaySrc = getDescImageSrc(editQ, !!pendingDescPreview);
                    return (
                      <div className="relative">
                        <img
                          src={displaySrc}
                          alt="Izoh rasmi"
                          className="block mx-auto max-w-full max-h-56 rounded bg-white cursor-zoom-in object-contain"
                          onClick={() => setPreviewDescImage(displaySrc)}
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        {pendingDescPreview && (
                          <p className="text-xs text-yellow-400 mt-1">⏳ Yangi fayl tanlandi (saqlashni bosing)</p>
                        )}
                        <button
                          onClick={() => {
                            setPendingDescFile(null);
                            setPendingDescPreview(null);
                            setEditQ(prev => ({ ...prev, explanation_image: '' }));
                          }}
                          className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs cursor-pointer"
                        >×</button>
                      </div>
                    );
                  })() : (
                    <p className="text-slate-500 text-xs">Izoh rasmi kiritilmagan</p>
                  )}
                </div>
              ) : (
                currentQ.explanation_image ? (() => {
                  const displaySrc = mediaUrl(currentQ.explanation_image);
                  return (
                    <div>
                      <img
                        src={displaySrc}
                        alt="Izoh rasmi"
                        className="block mx-auto max-w-full max-h-56 rounded bg-white cursor-zoom-in object-contain border border-white/10 hover:border-blue-400 transition-all"
                        onClick={() => setPreviewDescImage(displaySrc)}
                        title="Kattalashtirib ko'rish"
                      />
                    </div>
                  );
                })() : (
                  <p className="text-slate-500 text-xs">Izoh rasmi yo'q</p>
                )
              )}
            </div>
          </div>

          {/* O'ng tomon: Savol rasmi */}
          <div className="min-w-0 md:h-full">
            {/* Rasm komponenti */}
            <QuestionImageComponent
              currentItem={imageItem}
              editing={editing}
              onClickImage={(src) => setPreviewImage(src)}
              fileInputRef={fileInputRef}
              onImageChange={handleImageChange}
              previewActive={!!previewImage}
            >
              {previewImage && (
                <ImagePreview
                  src={previewImage}
                  onClose={() => setPreviewImage(null)}
                  onSave={async (dataUrl) => {
                    if (currentQ && uploadQuestionImage) {
                      const res = await fetch(dataUrl);
                      const blob = await res.blob();
                      const file = new File([blob], `q_${currentQ.id}_crop.jpg`, { type: 'image/jpeg' });
                      await uploadQuestionImage(currentQ.id, file);
                    }
                    setPreviewImage(null);
                  }}
                />
              )}
            </QuestionImageComponent>
          </div>
        </div>
      </div>
    </div>

      {/* ─── Paginatsiya (pastda turadi, kontent ustiga chiqmaydi) ─── */}
      <div
        className="shrink-0 sticky bottom-0 flex items-center gap-2 justify-between"
        style={{
          zIndex: 1000,
          padding: '10px',
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(8px)',
          borderTop: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <button
          className="btn rounded-sm border-gray-700 text-white bg-gray-500 cursor-pointer"
          onClick={handlePrev}
        >
          <MdKeyboardDoubleArrowLeft size={20} />
        </button>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={questionsList.map(q => q.id)}>
            <div className="flex flex-wrap gap-1 items-center justify-center max-w-[80vw] overflow-x-auto">
              {questionsList.map((q, idx) => (
                <SortableQuestionNum key={q.id} id={q.id} index={idx}
                  isActive={idx === activeIndex}
                  onClick={() => { if (editing) { saveEdit(); } setActiveIndex(idx); }} />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        <div className="flex items-center gap-1">
          <button onClick={handleAddQuestion}
            className="btn rounded-sm border-blue-700 text-blue-400 bg-blue-950/60 cursor-pointer px-3 py-1"
            style={{ fontSize: '16px' }}>
            ＋
          </button>
          <button
            className="btn rounded-sm border-gray-700 text-white bg-gray-500 cursor-pointer"
            onClick={handleNext}
          >
            <MdKeyboardDoubleArrowRight size={20} />
          </button>
        </div>
      </div>

      {/* ─── Darsni tanlash modali ─── */}
      {showLessonPicker && (
        <div
          className="fixed inset-0 z-[2000] flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setShowLessonPicker(false)}
        >
          <div
            className="bg-slate-900 rounded-lg p-4 max-w-md w-full max-h-[70vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-bold text-white">📁 Boshqa mavzuga ko'chirish</h3>
              <button
                onClick={() => setShowLessonPicker(false)}
                className="text-slate-400 hover:text-white text-xl cursor-pointer"
              >×</button>
            </div>
            <div className="overflow-y-auto flex-1">
              {sections.map(sec => (
                <div key={sec.id} className="mb-3">
                  <h4 className="text-sm font-semibold text-orange-300 mb-1 px-2">
                    {getVal(sec, 'name')}
                  </h4>
                  <div className="flex flex-col gap-1">
                    {lessons.filter(l => l.section === sec.id).map(les => (
                      <button
                        key={les.id}
                        onClick={() => handleMoveToLesson(les.id)}
                        disabled={les.id === lid}
                        className={`text-left px-3 py-2 rounded text-sm transition-colors cursor-pointer ${
                          les.id === lid
                            ? 'bg-green-900/40 text-green-300 cursor-not-allowed'
                            : 'bg-slate-800 text-slate-200 hover:bg-blue-900/50 hover:text-white'
                        }`}
                      >
                        {les.id === lid && '✓ '}{getVal(les, 'name')}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Izoh rasmini to'liq o'lchamda ko'rish modali ─── */}
      {previewDescImage && (
        <div
          className="fixed inset-0 z-[2500] flex items-center justify-center p-4 cursor-pointer"
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(5px)' }}
          onClick={() => setPreviewDescImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setPreviewDescImage(null)}
              className="absolute -top-10 right-0 text-white text-2xl font-bold hover:text-red-400 cursor-pointer bg-transparent border-none"
            >✕</button>
            <img
              src={previewDescImage}
              alt="Izoh rasmi to'liq"
              className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
            />
          </div>
        </div>
      )}

    </div>
  );
}
