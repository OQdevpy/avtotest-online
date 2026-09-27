import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from 'react-icons/md';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useData } from '../context/DataContext';
import ImagePreview from '../components/ImagePreview';

// ─── Sortable savol raqami (darslik paginatsiya uslubida) ───
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

// ─── Rasm komponenti (darslik ImageComponent bilan bir xil) ───
function QuestionImageComponent({ currentItem, editing, onClickImage, onClickUpload, fileInputRef, onImageChange, previewActive, children }) {
  const [containerHeight, setContainerHeight] = useState('560px');

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
  // Backenddan kelgan nisbiy yo'l (masalan "images/q55.webp") → "/media/images/q55.webp"
  const resolvedSrc = hasImage
    ? (imageSrc.startsWith('data:') ? imageSrc : `/media/${imageSrc}`)
    : '/media/default_image.jpg';

  return (
    <div
      className="md:w-[60%] w-full flex items-center justify-center cursor-pointer"
      style={{
        maxHeight: containerHeight,
        minHeight: containerHeight,
        boxShadow: '0 0 10px rgba(0, 0, 0, 0.1)',
        background: previewActive ? '#1a1a2e' : '#ffffff',
      }}
      onClick={() => {
        if (previewActive) return;
        if (editing) {
          fileInputRef?.current?.click();
        } else {
          onClickImage(resolvedSrc);
        }
      }}
    >
      {previewActive ? children : (
        <>
          <img
            src={resolvedSrc}
            alt="Savol rasmi"
            className="object-contain w-full"
            style={{ maxWidth: '100%', maxHeight: '100%' }}
            onError={(e) => { e.target.src = '/media/default_image.jpg'; }}
          />
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
  const [pendingImageFile, setPendingImageFile] = useState(null); // Haqiqiy File obyekti
  const [pendingImagePreview, setPendingImagePreview] = useState(null); // Ko'rish uchun dataUrl
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
      // Backend: text_uz, text_ru, text_cry (question_uz emas!)
      text_uz: currentQ.text_uz,
      text_ru: currentQ.text_ru,
      text_cry: currentQ.text_cry,
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

  // Tahrirlashni saqlash — rasmlar multipart bilan yuklanadi
  const saveEdit = async () => {
    if (!currentQ) return;

    // Avval savol maydonlarini yangilash (PATCH)
    const questionUpdate = {
      text_uz: editQ.text_uz,
      text_ru: editQ.text_ru,
      text_cry: editQ.text_cry,
      is_in_web: editQ.is_in_web,
      is_published: editQ.is_published,
    };
    await updateQuestion(currentQ.id, questionUpdate);

    // Asosiy rasm yuklash (agar yangi fayl tanlangan bo'lsa)
    if (pendingImageFile && uploadQuestionImage) {
      await uploadQuestionImage(currentQ.id, pendingImageFile);
    }

    // Izoh rasmi yuklash
    if (pendingDescFile && uploadExplanationImage) {
      await uploadExplanationImage(currentQ.id, pendingDescFile);
    }

    // Javoblarni yangilash
    for (const a of editAnswers) {
      if (a._new) {
        // Yangi javob allaqachon addAnswer orqali yaratilgan
      } else {
        // Backend: text_uz, text_ru, text_cry (answer_uz emas!)
        await updateAnswer(a.id, {
          text_uz: a.text_uz, text_ru: a.text_ru, text_cry: a.text_cry, is_true: a.is_true,
        });
      }
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

  // Asosiy rasm tanlash — haqiqiy File saqlash
  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingImageFile(file);
    // Ko'rish uchun URL yaratish
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
    return `/media/${value}`;
  };

  // Savolni boshqa darsga ko'chirish
  const handleMoveToLesson = async (newLessonId) => {
    if (!currentQ || newLessonId === lid) return;
    // Backend: lesson maydoni FK
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

  // Ko'rsatish uchun: agar tahrirda yangi rasm tanlangan bo'lsa preview, aks holda saqlangan yo'l
  const imageSrc = editing
    ? (pendingImagePreview || editQ.image)
    : currentQ.image;
  const displayAnswers = editing ? editAnswers : currentAnswers;
  const imageItem = { image: imageSrc || '' };

  return (
    <div className="container max-w-full flex flex-col gap-5">
      {/* ─── Sarlavha qatori ─── */}
      <div className="flex flex-col gap-0.5">
        <div className="flex justify-between gap-2 items-center">
          <h2 className="text-xl md:text-lg font-bold text-red-100">
            {lesson && getVal(lesson, 'name')}
          </h2>

          <div className="flex-shrink-0 flex items-center gap-2 min-w-[280px] justify-end">
            {!editing && (
              <>
                <button
                  onClick={() => setShowLessonPicker(true)}
                  className="px-2.5 py-0.5 rounded text-xs font-semibold text-orange-300 border border-orange-500/30 cursor-pointer hover:bg-orange-500/20"
                  style={{ background: 'rgba(249,115,22,0.15)' }}
                >
                  📁 Boshqa mavzu
                </button>
                {/* Nashr holati belgisi */}
                <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                  currentQ.is_published
                    ? 'text-emerald-300 border border-emerald-500/30'
                    : 'text-amber-300 border border-amber-500/30'
                }`} style={{ background: currentQ.is_published ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.15)' }}>
                  {currentQ.is_published ? '✓ Nashr' : '⏳ Qoralama'}
                </span>
                <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                  currentQ.is_in_web
                    ? 'text-green-300 border border-green-500/30'
                    : 'text-red-300 border border-red-500/20'
                }`} style={{ background: currentQ.is_in_web ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.15)' }}>
                  {currentQ.is_in_web ? '✓ Web' : '✕ Web'}
                </span>
              </>
            )}
            {editing ? (
              <>
                {/* Nashr etish toggle */}
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  {editQ.is_published ? 'Nashr' : 'Qoralama'}
                  <div className={`w-9 h-5 rounded-full relative cursor-pointer transition-colors ${editQ.is_published ? 'bg-emerald-500' : 'bg-slate-600'}`}
                    onClick={() => setEditQ(prev => ({ ...prev, is_published: !prev.is_published }))}>
                    <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all ${editQ.is_published ? 'left-4.5' : 'left-0.5'}`} />
                  </div>
                </div>
                {/* is_in_web toggle */}
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  {t('isInWeb')}
                  <div className={`w-9 h-5 rounded-full relative cursor-pointer transition-colors ${editQ.is_in_web ? 'bg-green-500' : 'bg-slate-600'}`}
                    onClick={() => setEditQ(prev => ({ ...prev, is_in_web: !prev.is_in_web }))}>
                    <div className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all ${editQ.is_in_web ? 'left-4.5' : 'left-0.5'}`} />
                  </div>
                </div>
                <button onClick={() => { if(confirm("O'chirish?")) { deleteQuestion(currentQ.id); setEditing(false); } }}
                  className="btn bg-red-950/60 text-white flex items-center border border-red-900 p-2 cursor-pointer hover:bg-red-950/80"
                  style={{ fontSize: '13px' }}>
                  🗑️ {t('delete')}
                </button>
                <button onClick={saveEdit}
                  className="btn bg-green-950/60 text-white flex items-center border border-green-900 p-2 cursor-pointer hover:bg-green-950/80"
                  style={{ fontSize: '13px' }}>
                  💾 {t('save')}
                </button>
              </>
            ) : (
              <button
                className="btn bg-blue-950/60 text-white flex items-center border border-blue-900 p-2 cursor-pointer w-full hover:bg-blue-950/60"
                onClick={startEdit}
                style={{ width: '100%' }}
              >
                ✏️ {t('edit')}
              </button>
            )}
          </div>
        </div>

        {/* ─── Savol matni ─── */}
        {editing ? (
          <div className="font-bold text-white bg-blue-900/30 flex justify-center items-center"
            style={{ fontSize: '19px' }}>
            <textarea value={editQ[`text_${lang}`] || ''}
              onChange={e => setEditQ(prev => ({ ...prev, [`text_${lang}`]: e.target.value }))}
              rows={2}
              className="w-full bg-transparent border border-blue-500 text-white text-center font-bold resize-none outline-none p-1"
              style={{ fontSize: '19px' }} />
          </div>
        ) : (
          <h2 className="font-bold text-white bg-blue-900/30 flex justify-center items-center"
            style={{ fontSize: '19px' }}>
            {getVal(currentQ, 'text')}
          </h2>
        )}
      </div>

      {/* ─── Asosiy qism: javoblar + rasm ─── */}
      <div className="min-h-20">
        <div className="flex flex-col md:flex-row justify-between gap-4">
          {/* Javoblar ustuni */}
          <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full">
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
                    {/* Backend: text_uz, text_ru, text_cry (answer_uz emas!) */}
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
                      {/* Backend: text_uz, text_ru, text_cry */}
                      {getVal(answer, 'text')}
                    </h2>
                  </>
                )}
              </div>
            ))}
            {editing && (
              <button onClick={() => {
                const newA = addAnswer(currentQ.id);
                if (newA) setEditAnswers(prev => [...prev, { ...newA, _new: true }]);
              }}
                className="flex items-center justify-center gap-1 rounded-md px-4 py-2 mt-1 cursor-pointer text-blue-400 text-xs"
                style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}>
                ＋ {t('addAnswer')}
              </button>
            )}

            {/* Izoh rasmi bo'limi */}
            <div className="mt-4 p-3 rounded-lg" style={{ background: 'rgba(100,140,220,0.1)', border: '1px solid rgba(100,140,220,0.3)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-blue-300 font-semibold">📝 Izoh rasmi</span>
                {editing && (
                  <div className="flex gap-1">
                    <button
                      onClick={() => descImageInputRef.current?.click()}
                      className="text-xs px-2 py-1 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700"
                    >
                      📁 Fayldan
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
                  {(pendingDescPreview || currentQ.explanation_image) ? (() => {
                    const displaySrc = getDescImageSrc(currentQ, !!pendingDescPreview);
                    return (
                      <div className="relative">
                        <img
                          src={displaySrc}
                          alt="Izoh rasmi"
                          className="max-h-32 rounded cursor-pointer"
                          onClick={() => setPreviewDescImage(displaySrc)}
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                        {pendingDescPreview && (
                          <p className="text-xs text-yellow-400 mt-1">⏳ Saqlanmagan (yangi fayl)</p>
                        )}
                        <button
                          onClick={() => {
                            setPendingDescFile(null);
                            setPendingDescPreview(null);
                          }}
                          className="absolute top-1 right-1 bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs cursor-pointer"
                        >×</button>
                      </div>
                    );
                  })() : (
                    <p className="text-slate-500 text-xs">Izoh rasmi yo'q</p>
                  )}
                </div>
              ) : (
                currentQ.explanation_image ? (() => {
                  const displaySrc = `/media/${currentQ.explanation_image}`;
                  return (
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <span className="text-xs text-green-400 flex-1">📁 {currentQ.explanation_image}</span>
                      </div>
                      <img
                        src={displaySrc}
                        alt="Izoh rasmi"
                        className="max-h-32 rounded cursor-pointer"
                        onClick={() => setPreviewDescImage(displaySrc)}
                      />
                    </div>
                  );
                })() : (
                  <p className="text-slate-500 text-xs">Izoh rasmi yo'q</p>
                )
              )}
            </div>
          </div>

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
                    // dataUrl'dan File yaratish
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

      {/* ─── Paginatsiya (pastda qotib turadi) ─── */}
      <div
        className="flex items-center gap-2 justify-between"
        style={{
          position: 'fixed',
          bottom: '0',
          left: '0',
          right: '0',
          zIndex: 1000,
          padding: '10px',
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
            <div className="flex flex-wrap gap-1 items-center justify-center">
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

    </div>
  );
}
