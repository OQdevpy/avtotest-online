import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useData } from '../context/DataContext';

// Sudrab tartiblash uchun dars elementi
function SortableLessonItem({ lesson, isEditing, editValues, setEditValues, lang, getVal, onStartEdit, onSaveEdit, onDelete, onNavigate, onMove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: lesson.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.7 : 1,
    zIndex: isDragging ? 100 : 'auto',
  };

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        background: isEditing ? 'rgba(30,60,140,0.4)' : 'rgba(20,40,80,0.5)',
        border: `1px solid ${isEditing ? '#3b82f6' : 'rgba(100,140,220,0.2)'}`,
      }}
      className="flex items-center rounded-md px-5 py-3.5 cursor-pointer transition-all gap-3"
      onClick={() => !isEditing && onNavigate()}
    >
      {/* Sudrab tortish tutqichi */}
      <span
        {...attributes}
        {...listeners}
        className="cursor-grab text-slate-500 hover:text-slate-300 px-1"
        onClick={(e) => e.stopPropagation()}
      >
        ⋮⋮
      </span>

      {isEditing ? (
        <>
          <input
            value={editValues[`name_${lang}`] || ''}
            onChange={(e) => setEditValues((prev) => ({ ...prev, [`name_${lang}`]: e.target.value }))}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.key === 'Enter' && onSaveEdit()}
            autoFocus
            className="flex-1 text-center text-base bg-black/30 border border-blue-500 text-white px-3 py-1.5 rounded outline-none"
          />
          <span
            className="text-green-400 cursor-pointer text-lg"
            onClick={(e) => {
              e.stopPropagation();
              onSaveEdit();
            }}
          >
            💾
          </span>
          <span
            className="text-red-400 cursor-pointer text-sm"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm("O'chirish?")) onDelete();
            }}
          >
            🗑️
          </span>
        </>
      ) : (
        <>
          <span className="flex-1 text-center text-base" style={{ color: '#c8d6e5' }}>
            {getVal(lesson, 'name')}
          </span>
          <span
            className="text-orange-300 cursor-pointer text-base"
            title="Boshqa bo'limga ko'chirish"
            onClick={(e) => {
              e.stopPropagation();
              onMove();
            }}
          >
            📁
          </span>
          <span
            className="edit-trigger text-blue-400 cursor-pointer text-base"
            onClick={(e) => {
              e.stopPropagation();
              onStartEdit();
            }}
          >
            ✏️
          </span>
        </>
      )}
    </div>
  );
}

export default function Lessons() {
  const { sectionId } = useParams();
  const sid = Number(sectionId);
  const { sections, getLessonsBySection, updateLesson, addLesson, deleteLesson, reorderLessons, moveLesson, getVal, t, lang } = useData();
  const navigate = useNavigate();
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  // Boshqa bo'limga ko'chirilayotgan mavzu (oyna ochiq bo'lsa)
  const [movingLesson, setMovingLesson] = useState(null);
  const [moving, setMoving] = useState(false);

  const section = sections.find((s) => s.id === sid);
  const lessons = getLessonsBySection(sid);

  const startEdit = (lesson) => {
    setEditingId(lesson.id);
    setEditValues({ name_uz: lesson.name_uz, name_ru: lesson.name_ru, name_cry: lesson.name_cry });
  };

  const saveEdit = async () => {
    if (editingId) {
      await updateLesson(editingId, editValues);
      setEditingId(null);
    }
  };

  const handleAdd = async () => {
    const newL = await addLesson(sid);
    if (newL) startEdit(newL);
  };

  const handleMove = async (targetSectionId) => {
    if (!movingLesson || moving || targetSectionId === sid) return;
    setMoving(true);
    try {
      await moveLesson(movingLesson.id, targetSectionId);
      setMovingLesson(null);
    } catch (err) {
      console.error('Lesson move error:', err);
      alert("Ko'chirishda xatolik yuz berdi. Qayta urinib ko'ring.");
    } finally {
      setMoving(false);
    }
  };

  // Drag-and-drop
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const ids = lessons.map((l) => l.id);
    const oldIdx = ids.indexOf(active.id);
    const newIdx = ids.indexOf(over.id);
    const newIds = arrayMove(ids, oldIdx, newIdx);

    reorderLessons(sid, newIds);
  };

  return (
    <div className="flex flex-col items-center px-6 py-10">
      <div className="w-full max-w-[720px] flex flex-col gap-2">
        {section && (
          <div className="text-red-400 text-sm font-medium mb-3 pl-1">{getVal(section, 'name')}</div>
        )}

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={lessons.map((l) => l.id)} strategy={verticalListSortingStrategy}>
            {lessons.map((lesson) => (
              <SortableLessonItem
                key={lesson.id}
                lesson={lesson}
                isEditing={editingId === lesson.id}
                editValues={editValues}
                setEditValues={setEditValues}
                lang={lang}
                getVal={getVal}
                onStartEdit={() => startEdit(lesson)}
                onSaveEdit={saveEdit}
                onDelete={() => deleteLesson(lesson.id)}
                onNavigate={() => navigate(`/sections/${sid}/lessons/${lesson.id}/questions`)}
                onMove={() => setMovingLesson(lesson)}
              />
            ))}
          </SortableContext>
        </DndContext>

        <button
          onClick={handleAdd}
          className="flex items-center justify-center gap-2 rounded-md px-5 py-3 cursor-pointer text-blue-400 text-sm transition-all hover:border-blue-500"
          style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}
        >
          ＋ {t('addLesson')}
        </button>
      </div>

      {movingLesson && (
        <div
          className="fixed inset-0 z-[2000] flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => !moving && setMovingLesson(null)}
        >
          <div
            className="bg-slate-900 rounded-lg p-4 max-w-md w-full max-h-[70vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-lg font-bold text-white">📁 Boshqa bo'limga ko'chirish</h3>
              <button
                onClick={() => setMovingLesson(null)}
                disabled={moving}
                className="text-slate-400 hover:text-white text-xl cursor-pointer"
              >×</button>
            </div>
            <p className="text-sm text-slate-400 mb-3">
              {getVal(movingLesson, 'name')} — savollari bilan birga ko'chadi
            </p>
            <div className="overflow-y-auto flex-1 flex flex-col gap-1">
              {[...sections].sort((a, b) => (a.order || 0) - (b.order || 0)).map((sec) => (
                <button
                  key={sec.id}
                  onClick={() => handleMove(sec.id)}
                  disabled={sec.id === sid || moving}
                  className={`text-left px-3 py-2 rounded text-sm transition-colors cursor-pointer disabled:cursor-not-allowed ${
                    sec.id === sid
                      ? 'bg-green-900/40 text-green-300'
                      : 'bg-slate-800 text-slate-200 hover:bg-blue-900/50 hover:text-white disabled:opacity-50'
                  }`}
                >
                  {sec.id === sid && '✓ '}{getVal(sec, 'name')}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
