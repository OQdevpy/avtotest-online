import { useState } from 'react';
import { useData } from '../context/DataContext';
import JSZip from 'jszip';
import { BACKEND_URL, mediaUrl } from '../services/api';

export default function QuestionPickerModal({ blits, onClose }) {
  const {
    sections,
    getLessonsBySection,
    getQuestionsByLesson,
    getQuestionById,
    getVal,
    t,
    addQuestionToBlits,
    removeQuestionFromBlits,
  } = useData();

  const [selectedSectionId, setSelectedSectionId] = useState(sections[0]?.id || null);
  const [selectedLessonId, setSelectedLessonId] = useState(null);

  // blits.items dan mavjud question id larni olish
  const initialQIds = new Set((blits.items || []).map(i => i.question));
  const [selectedQIds, setSelectedQIds] = useState(initialQIds);
  const [isExporting, setIsExporting] = useState(false);

  const sectionLessons = selectedSectionId ? getLessonsBySection(selectedSectionId) : [];
  const lessonQuestions = selectedLessonId ? getQuestionsByLesson(selectedLessonId) : [];

  const toggleQuestion = (qId) => {
    setSelectedQIds(prev => {
      const next = new Set(prev);
      if (next.has(qId)) next.delete(qId);
      else next.add(qId);
      return next;
    });
  };

  const handleSave = async () => {
    const existingQIds = (blits.items || []).map(i => i.question);
    
    // O'chirilganlarni chiqarish
    for (const qId of existingQIds) {
      if (!selectedQIds.has(qId)) {
        await removeQuestionFromBlits(blits.id, qId);
      }
    }
    // Yangi qo'shilganlarni qo'shish
    for (const qId of selectedQIds) {
      if (!existingQIds.includes(qId)) {
        await addQuestionToBlits(blits.id, qId);
      }
    }
    onClose();
  };

  const getImageUrl = (imagePath) => {
    if (!imagePath) return null;
    if (String(imagePath).startsWith('data:')) return imagePath;
    if (String(imagePath).startsWith('http://') || String(imagePath).startsWith('https://')) return imagePath;

    const normalized = String(imagePath).replace(/^\/+/, '');
    if (normalized.startsWith('media/')) return `${BACKEND_URL}/${normalized}`;
    return mediaUrl(normalized);
  };

  const safeFileName = (value) => value.replace(/[\\/:*?"<>|]/g, '_');

  const extractFileName = (question, contentType) => {
    const imagePath = String(question.image || '').trim();

    if (imagePath.startsWith('data:')) {
      const ext = (contentType?.split('/')[1] || 'png').split(';')[0].toLowerCase();
      return `question_${question.id}.${ext}`;
    }

    const rawName = imagePath.split('/').pop() || `question_${question.id}.png`;
    let decoded = rawName;
    try {
      decoded = decodeURIComponent(rawName);
    } catch {
      decoded = rawName;
    }
    return `question_${question.id}_${safeFileName(decoded)}`;
  };

  const handleExportImages = async () => {
    try {
      setIsExporting(true);

      const selectedQuestions = Array.from(selectedQIds)
        .map((qId) => getQuestionById(qId))
        .filter(Boolean)
        .filter((q) => q.image && String(q.image).trim() !== '');

      if (selectedQuestions.length === 0) {
        alert(t('noImagesToExport'));
        return;
      }

      const zip = new JSZip();
      let exportedCount = 0;

      for (const question of selectedQuestions) {
        const imageUrl = getImageUrl(question.image);
        if (!imageUrl) continue;

        try {
          const response = await fetch(
            imageUrl.startsWith('data:') ? imageUrl : encodeURI(imageUrl)
          );
          if (!response.ok) continue;

          const blob = await response.blob();
          const fileName = extractFileName(question, blob.type);
          zip.file(fileName, blob);
          exportedCount += 1;
        } catch (error) {
          console.warn('Image export skipped for question:', question.id, error);
        }
      }

      if (exportedCount === 0) {
        alert(t('noImagesToExport'));
        return;
      }

      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(zipBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blits_${blits.id}_images.zip`;
      a.click();
      URL.revokeObjectURL(url);

      alert(`${t('imagesExported')}: ${exportedCount}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.75)' }}
      onClick={onClose}>
      <div className="rounded-xl flex flex-col overflow-hidden" onClick={e => e.stopPropagation()}
        style={{ background: '#1e293b', border: '1px solid #334155', width: '90vw', maxWidth: '960px', height: '75vh' }}>

        {/* Header */}
        <div className="px-5 py-3.5 flex justify-between items-center" style={{ background: '#0f172a', borderBottom: '1px solid #334155' }}>
          <h3 className="text-sm font-medium">📋 {t('selectQuestions')}</h3>
          <button onClick={onClose} className="text-slate-400 text-xl cursor-pointer hover:text-white bg-transparent border-none">✕</button>
        </div>

        {/* Body: 3 columns */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sections col */}
          <div className="w-[180px] flex flex-col overflow-y-auto" style={{ borderRight: '1px solid #334155' }}>
            <div className="px-3.5 py-2.5 text-xs text-slate-500 uppercase tracking-wider shrink-0"
              style={{ background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid #334155' }}>
              {t('sections')}
            </div>
            {sections.map(s => (
              <div key={s.id}
                className={`px-3.5 py-2.5 text-sm cursor-pointer transition-colors ${
                  s.id === selectedSectionId ? 'text-blue-400' : 'text-slate-300 hover:bg-white/5'
                }`}
                style={{
                  background: s.id === selectedSectionId ? 'rgba(59,130,246,0.15)' : 'transparent',
                  borderLeft: s.id === selectedSectionId ? '3px solid #3b82f6' : '3px solid transparent',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}
                onClick={() => { setSelectedSectionId(s.id); setSelectedLessonId(null); }}>
                {getVal(s, 'name')}
              </div>
            ))}
          </div>

          {/* Lessons col */}
          <div className="w-[220px] flex flex-col overflow-y-auto" style={{ borderRight: '1px solid #334155' }}>
            <div className="px-3.5 py-2.5 text-xs text-slate-500 uppercase tracking-wider shrink-0"
              style={{ background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid #334155' }}>
              {t('lessons')}
            </div>
            {sectionLessons.map(l => {
              const lQuestions = getQuestionsByLesson(l.id);
              const selectedCount = lQuestions.filter(q => selectedQIds.has(q.id)).length;
              return (
              <div key={l.id}
                className={`px-3.5 py-2.5 text-sm cursor-pointer transition-colors flex items-center justify-between gap-1 ${
                  l.id === selectedLessonId ? 'text-blue-400' : 'text-slate-300 hover:bg-white/5'
                }`}
                style={{
                  background: l.id === selectedLessonId ? 'rgba(59,130,246,0.15)' : 'transparent',
                  borderLeft: l.id === selectedLessonId ? '3px solid #3b82f6' : '3px solid transparent',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                }}
                onClick={() => setSelectedLessonId(l.id)}>
                <span className="truncate">{getVal(l, 'name')}</span>
                {selectedCount > 0 && (
                  <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{ background: 'rgba(34,197,94,0.25)', color: '#4ade80', minWidth: '20px', textAlign: 'center' }}>
                    {selectedCount}
                  </span>
                )}
              </div>
              );
            })}
          </div>

          {/* Questions col */}
          <div className="flex-1 flex flex-col overflow-y-auto">
            <div className="px-3.5 py-2.5 text-xs text-slate-500 uppercase tracking-wider shrink-0"
              style={{ background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid #334155' }}>
              {t('questions')}
            </div>
            {lessonQuestions.map(q => (
              <div key={q.id} className="flex items-start gap-2.5 px-3.5 py-2.5 hover:bg-white/3"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                <input type="checkbox" checked={selectedQIds.has(q.id)}
                  onChange={() => toggleQuestion(q.id)}
                  className="w-4.5 h-4.5 mt-0.5 accent-blue-500 cursor-pointer shrink-0" />
                <div>
                  <div className="text-sm leading-relaxed">{getVal(q, 'text')}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    ID: {q.id} {q.image && ' · 🖼️'}
                  </div>
                </div>
              </div>
            ))}
            {selectedLessonId && lessonQuestions.length === 0 && (
              <div className="text-center text-slate-500 py-8 text-sm">Savollar topilmadi</div>
            )}
            {!selectedLessonId && (
              <div className="text-center text-slate-500 py-8 text-sm">Darsni tanlang</div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 flex items-center gap-2.5" style={{ background: '#0f172a', borderTop: '1px solid #334155' }}>
          <span className="text-slate-500 text-xs mr-auto">{selectedQIds.size} ta savol tanlangan</span>
          <button onClick={handleExportImages}
            disabled={isExporting || selectedQIds.size === 0}
            className="px-4 py-2 text-xs cursor-pointer rounded disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: 'rgba(59,130,246,0.18)', border: '1px solid rgba(59,130,246,0.4)', color: '#60a5fa' }}>
            🖼️ {isExporting ? t('exporting') : t('exportImages')}
          </button>
          <button onClick={onClose}
            className="px-4 py-2 text-xs cursor-pointer rounded"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)', color: '#e2e8f0' }}>
            {t('cancel')}
          </button>
          <button onClick={handleSave}
            className="px-4 py-2 text-xs cursor-pointer rounded"
            style={{ background: 'rgba(34,197,94,0.2)', border: '1px solid rgba(34,197,94,0.4)', color: '#4ade80' }}>
            💾 {t('save')}
          </button>
        </div>
      </div>
    </div>
  );
}
