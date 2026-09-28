import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../context/DataContext';

export default function Sections() {
  const { sections, updateSection, addSection, deleteSection, getVal, t, lang } = useData();
  const navigate = useNavigate();
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});

  const startEdit = (section) => {
    setEditingId(section.id);
    setEditValues({ name_uz: section.name_uz, name_ru: section.name_ru, name_cry: section.name_cry });
  };

  const saveEdit = async () => {
    if (editingId) {
      await updateSection(editingId, editValues);
      setEditingId(null);
    }
  };

  const handleAdd = async () => {
    const newS = await addSection();
    if (newS) startEdit(newS);
  };

  // Backend: order maydoni (eski tartib emas)
  const sorted = [...(Array.isArray(sections) ? sections : [])].sort((a, b) => (a.order || 0) - (b.order || 0));

  return (
    <div className="flex flex-col items-center px-6 py-10">
      <div className="w-full max-w-[720px] flex flex-col gap-2">
        {sorted.map(section => (
          <div key={section.id}
            className={`flex items-center rounded-md px-5 py-3.5 cursor-pointer transition-all gap-3 ${
              editingId === section.id ? 'border-blue-500' : 'hover:border-blue-400/40'
            }`}
            style={{
              background: editingId === section.id ? 'rgba(30,60,140,0.4)' : 'rgba(20,40,80,0.5)',
              border: `1px solid ${editingId === section.id ? '#3b82f6' : 'rgba(100,140,220,0.2)'}`,
            }}
            onClick={() => editingId !== section.id && navigate(`/sections/${section.id}/lessons`)}>

            {editingId === section.id ? (
              <>
                <input value={editValues[`name_${lang}`] || ''}
                  onChange={e => setEditValues(prev => ({ ...prev, [`name_${lang}`]: e.target.value }))}
                  onClick={e => e.stopPropagation()}
                  onKeyDown={e => e.key === 'Enter' && saveEdit()}
                  autoFocus
                  className="flex-1 text-center text-base bg-black/30 border border-blue-500 text-white px-3 py-1.5 rounded outline-none" />
                <span className="text-green-400 cursor-pointer text-lg"
                  onClick={e => { e.stopPropagation(); saveEdit(); }}>💾</span>
                <span className="text-red-400 cursor-pointer text-sm"
                  onClick={e => { e.stopPropagation(); if(confirm("O'chirish?")) deleteSection(section.id); }}>🗑️</span>
              </>
            ) : (
              <>
                <span className="flex-1 text-center text-base" style={{ color: '#c8d6e5' }}>
                  {getVal(section, 'name')}
                </span>
                <span className="edit-trigger text-blue-400 cursor-pointer text-base"
                  onClick={e => { e.stopPropagation(); startEdit(section); }}>✏️</span>
              </>
            )}
          </div>
        ))}

        <button onClick={handleAdd}
          className="flex items-center justify-center gap-2 rounded-md px-5 py-3 cursor-pointer text-blue-400 text-sm transition-all hover:border-blue-500"
          style={{ border: '2px dashed rgba(100,140,220,0.3)', background: 'transparent' }}>
          ＋ {t('addSection')}
        </button>
      </div>
    </div>
  );
}
