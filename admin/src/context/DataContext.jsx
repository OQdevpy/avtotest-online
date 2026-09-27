import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import JSZip from 'jszip';
import { fetchJSON, postJSON, patchJSON, deleteResource, uploadFile } from '../services/api';
import { useAuth } from './AuthContext';

const DataContext = createContext(null);

const translations = {
  uz: {
    home: "Bosh sahifa", sections: "Bo'limlar", lessons: "Darslar", questions: "Savollar",
    blits: "Blits", edit: "Tahrirlash", save: "Saqlash", cancel: "Bekor qilish",
    addSection: "Yangi bo'lim qo'shish", addLesson: "Yangi dars qo'shish",
    addQuestion: "Yangi savol qo'shish", addAnswer: "Javob qo'shish",
    addBlits: "Yangi blits qo'shish", selectQuestions: "Savollarni tanlash",
    exportImages: "Rasmlarni eksport", exporting: "Eksport...",
    noImagesToExport: "Tanlangan savollarda rasm yo'q",
    imagesExported: "Rasmlar eksport qilindi",
    delete: "O'chirish", back: "ORTGA", question: "Savol",
    correctAnswer: "To'g'ri javob", image: "Rasm", noImage: "Rasm yo'q",
    changeImage: "Rasm almashtirish", isInWeb: "is_in_web",
  },
  ru: {
    home: "Главная", sections: "Разделы", lessons: "Уроки", questions: "Вопросы",
    blits: "Блиц", edit: "Редактировать", save: "Сохранить", cancel: "Отмена",
    addSection: "Добавить раздел", addLesson: "Добавить урок",
    addQuestion: "Добавить вопрос", addAnswer: "Добавить ответ",
    addBlits: "Добавить блиц", selectQuestions: "Выбрать вопросы",
    exportImages: "Экспорт изображений", exporting: "Экспорт...",
    noImagesToExport: "У выбранных вопросов нет изображений",
    imagesExported: "Изображения экспортированы",
    delete: "Удалить", back: "НАЗАД", question: "Вопрос",
    correctAnswer: "Правильный ответ", image: "Рисунок", noImage: "Нет рисунка",
    changeImage: "Сменить рисунок", isInWeb: "is_in_web",
  },
  cry: {
    home: "Бош саҳифа", sections: "Бўлимлар", lessons: "Дарслар", questions: "Саволлар",
    blits: "Блиц", edit: "Таҳрирлаш", save: "Сақлаш", cancel: "Бекор қилиш",
    addSection: "Янги бўлим қўшиш", addLesson: "Янги дарс қўшиш",
    addQuestion: "Янги савол қўшиш", addAnswer: "Жавоб қўшиш",
    addBlits: "Янги блиц қўшиш", selectQuestions: "Саволларни танлаш",
    exportImages: "Расмларни экспорт", exporting: "Экспорт...",
    noImagesToExport: "Танланган саволларда расм йўқ",
    imagesExported: "Расмлар экспорт қилинди",
    delete: "Ўчириш", back: "ОРТГА", question: "Савол",
    correctAnswer: "Тўғри жавоб", image: "Расм", noImage: "Расм йўқ",
    changeImage: "Расм алмаштириш", isInWeb: "is_in_web",
  },
};

// DRF javobini xavfsiz massivga aylantirish (paginated bo'lsa results dan oladi)
function toList(res) {
  if (Array.isArray(res)) return res;
  if (res && Array.isArray(res.results)) return res.results;
  return [];
}

export function DataProvider({ children }) {
  const { user } = useAuth();
  const [sections, setSections] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState([]);
  const [blits, setBlits] = useState([]);
  const [lang, setLang] = useState('cry');
  const [loading, setLoading] = useState(true);

  // Ma'lumotlarni yuklash funksiyasi
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [sec, les, bli] = await Promise.all([
        fetchJSON('/manage/sections/?page_size=200'),
        fetchJSON('/manage/lessons/?page_size=200'),
        fetchJSON('/manage/blits/?page_size=200'),
      ]);
      setSections(toList(sec));
      setLessons(toList(les));
      setBlits(toList(bli));
      console.log('✅ Asosiy ma\'lumotlar backenddan yuklandi');
    } catch (err) {
      console.error('❌ Ma\'lumotlarni yuklashda xatolik:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Foydalanuvchi tizimga kirganida ma'lumotlarni yuklash
  useEffect(() => {
    if (user) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [user, loadData]);

  const t = useCallback((key) => translations[lang]?.[key] || key, [lang]);

  // Maydon nomlari backendda: question/answer uchun text, boshqalar uchun name
  const getVal = useCallback((obj, field) => {
    if (!obj) return '';
    const suffix = `_${lang}`;
    if (obj['text' + suffix] !== undefined && (field === 'question' || field === 'answer' || field === 'text')) {
      return obj['text' + suffix];
    }
    return obj[field + suffix] || obj[field + '_uz'] || '';
  }, [lang]);

  // ── Section CRUD ──
  const updateSection = useCallback(async (id, updates) => {
    try {
      const updated = await patchJSON(`/manage/sections/${id}/`, updates);
      setSections(prev => prev.map(s => s.id === id ? { ...s, ...updated } : s));
    } catch (err) {
      console.error('Section update error:', err);
    }
  }, []);
  
  const addSection = useCallback(async () => {
    try {
      const order = sections.length > 0 ? Math.max(...sections.map(s => s.order || 0)) + 1 : 1;
      const newS = await postJSON('/manage/sections/', {
        name_uz: "Yangi bo'lim", name_ru: "Новый раздел", name_cry: "Янги бўлим", order
      });
      setSections(prev => [...prev, newS]);
      return newS;
    } catch (err) {
      console.error('Section create error:', err);
    }
  }, [sections]);
  
  const deleteSection = useCallback(async (id) => {
    try {
      await deleteResource(`/manage/sections/${id}/`);
      setSections(prev => prev.filter(s => s.id !== id));
    } catch (err) {
      console.error('Section delete error:', err);
    }
  }, []);

  // ── Lesson CRUD ──
  const getLessonsBySection = useCallback((sectionId) =>
    sections && lessons
      ? lessons.filter(l => l.section === sectionId).sort((a, b) => (a.order || 0) - (b.order || 0))
      : [],
    [sections, lessons]
  );
    
  const updateLesson = useCallback(async (id, updates) => {
    try {
      const updated = await patchJSON(`/manage/lessons/${id}/`, updates);
      setLessons(prev => prev.map(l => l.id === id ? { ...l, ...updated } : l));
    } catch (err) {
      console.error('Lesson update error:', err);
    }
  }, []);
  
  const addLesson = useCallback(async (sectionId) => {
    try {
      const sectionLessons = lessons.filter(l => l.section === sectionId);
      const order = sectionLessons.length > 0 ? Math.max(...sectionLessons.map(l => l.order || 0)) + 1 : 1;
      const newL = await postJSON('/manage/lessons/', {
        section: sectionId, name_uz: "Yangi dars", name_ru: "Новый урок", name_cry: "Янги дарс", order
      });
      setLessons(prev => [...prev, newL]);
      return newL;
    } catch (err) {
      console.error('Lesson create error:', err);
    }
  }, [lessons]);
  
  const deleteLesson = useCallback(async (id) => {
    try {
      await deleteResource(`/manage/lessons/${id}/`);
      setLessons(prev => prev.filter(l => l.id !== id));
    } catch (err) {
      console.error('Lesson delete error:', err);
    }
  }, []);
  
  const reorderLessons = useCallback(async (sectionId, orderedIds) => {
    try {
      await postJSON('/manage/lessons/reorder/', { ids: orderedIds });
      setLessons(prev => prev.map(l => {
        if (l.section !== sectionId) return l;
        const idx = orderedIds.indexOf(l.id);
        return idx >= 0 ? { ...l, order: idx + 1 } : l;
      }));
    } catch (err) {
      console.error('Lesson reorder error:', err);
    }
  }, []);

  // ── Question CRUD ──
  const [loadedLessons, setLoadedLessons] = useState(new Set());
  
  const getQuestionsByLesson = useCallback((lessonId) => {
    if (!loadedLessons.has(lessonId)) {
      setLoadedLessons(prev => new Set(prev).add(lessonId));
      fetchJSON(`/manage/questions/?lesson=${lessonId}&page_size=200`).then(res => {
        const data = toList(res);
        setQuestions(prev => {
          const others = prev.filter(q => q.lesson !== lessonId);
          return [...others, ...data];
        });
        const newAnswers = [];
        data.forEach(q => {
          if (q.answers && Array.isArray(q.answers)) {
            newAnswers.push(...q.answers);
          }
        });
        if (newAnswers.length > 0) {
          setAnswers(prev => {
            const others = prev.filter(a => !data.find(q => q.id === a.question));
            return [...others, ...newAnswers];
          });
        }
      }).catch(err => {
        console.error('Questions fetch error:', err);
        setLoadedLessons(prev => {
          const s = new Set(prev);
          s.delete(lessonId);
          return s;
        });
      });
    }
    
    return questions
      .filter(q => q.lesson === lessonId)
      .sort((a, b) => (a.order || 0) - (b.order || 0));
  }, [questions, loadedLessons]);

  const getQuestionById = useCallback((id) => questions.find(q => q.id === id), [questions]);
  
  const updateQuestion = useCallback(async (id, updates) => {
    try {
      const updated = await patchJSON(`/manage/questions/${id}/`, updates);
      setQuestions(prev => prev.map(q => q.id === id ? { ...q, ...updated } : q));
    } catch (err) {
      console.error('Question update error:', err);
    }
  }, []);
  
  const addQuestion = useCallback(async (lessonId) => {
    try {
      const lessonQs = questions.filter(q => q.lesson === lessonId);
      const order = lessonQs.length > 0 ? Math.max(...lessonQs.map(q => q.order || 0)) + 1 : 1;
      const newQ = await postJSON('/manage/questions/', {
        lesson: lessonId,
        text_uz: "Yangi savol", text_ru: "Новый вопрос", text_cry: "Янги савол",
        order, is_in_web: false, is_published: true
      });
      setQuestions(prev => [...prev, newQ]);
      return newQ;
    } catch (err) {
      console.error('Question create error:', err);
    }
  }, [questions]);
  
  const deleteQuestion = useCallback(async (id) => {
    try {
      await deleteResource(`/manage/questions/${id}/`);
      setQuestions(prev => prev.filter(q => q.id !== id));
      setAnswers(prev => prev.filter(a => a.question !== id));
    } catch (err) {
      console.error('Question delete error:', err);
    }
  }, []);
  
  const reorderQuestions = useCallback(async (lessonId, orderedIds) => {
    try {
      await postJSON('/manage/questions/reorder/', { ids: orderedIds });
      setQuestions(prev => prev.map(q => {
        if (q.lesson !== lessonId) return q;
        const idx = orderedIds.indexOf(q.id);
        return idx >= 0 ? { ...q, order: idx + 1 } : q;
      }));
    } catch (err) {
      console.error('Question reorder error:', err);
    }
  }, []);

  // ── Answer CRUD ──
  const getAnswersByQuestion = useCallback((questionId) =>
    answers.filter(a => a.question === questionId).sort((a, b) => a.id - b.id), [answers]);
    
  const updateAnswer = useCallback(async (id, updates) => {
    try {
      const updated = await patchJSON(`/manage/answers/${id}/`, updates);
      setAnswers(prev => prev.map(a => a.id === id ? { ...a, ...updated } : a));
    } catch (err) {
      console.error('Answer update error:', err);
    }
  }, []);
  
  const addAnswer = useCallback(async (questionId) => {
    try {
      const newA = await postJSON('/manage/answers/', {
        question: questionId, text_uz: "", text_ru: "", text_cry: "", is_true: false
      });
      setAnswers(prev => [...prev, newA]);
      return newA;
    } catch (err) {
      console.error('Answer create error:', err);
    }
  }, []);
  
  const deleteAnswer = useCallback(async (id) => {
    try {
      await deleteResource(`/manage/answers/${id}/`);
      setAnswers(prev => prev.filter(a => a.id !== id));
    } catch (err) {
      console.error('Answer delete error:', err);
    }
  }, []);

  // ── Blits CRUD ──
  const updateBlits = useCallback(async (id, updates) => {
    try {
      const updated = await patchJSON(`/manage/blits/${id}/`, updates);
      setBlits(prev => prev.map(b => b.id === id ? { ...b, ...updated } : b));
    } catch (err) {
      console.error('Blits update error:', err);
    }
  }, []);
  
  const addBlits = useCallback(async () => {
    try {
      const newB = await postJSON('/manage/blits/', {
        name_uz: "Yangi blits", name_ru: "Новый блиц", name_cry: "Янги блиц"
      });
      newB.items = newB.items || [];
      setBlits(prev => [...prev, newB]);
      return newB;
    } catch (err) {
      console.error('Blits create error:', err);
    }
  }, []);
  
  const deleteBlits = useCallback(async (id) => {
    try {
      await deleteResource(`/manage/blits/${id}/`);
      setBlits(prev => prev.filter(b => b.id !== id));
    } catch (err) {
      console.error('Blits delete error:', err);
    }
  }, []);
  
  const addQuestionToBlits = useCallback(async (blitsId, questionId) => {
    try {
      const blitsObj = blits.find(b => b.id === blitsId);
      const currentItems = blitsObj?.items || [];
      const order = currentItems.length > 0 ? Math.max(...currentItems.map(i => i.order || 0)) + 1 : 1;
      
      const newBq = await postJSON('/manage/blits-questions/', {
        blits: blitsId, question: questionId, order
      });
      
      setBlits(prev => prev.map(b => {
        if (b.id !== blitsId) return b;
        return { ...b, items: [...(b.items || []), newBq] };
      }));
    } catch (err) {
      console.error('Blits question add error:', err);
    }
  }, [blits]);
  
  const removeQuestionFromBlits = useCallback(async (blitsId, questionId) => {
    try {
      const blitsObj = blits.find(b => b.id === blitsId);
      if (!blitsObj) return;
      const bqItem = blitsObj.items?.find(i => i.question === questionId);
      if (bqItem) {
        await deleteResource(`/manage/blits-questions/${bqItem.id}/`);
        setBlits(prev => prev.map(b => {
          if (b.id !== blitsId) return b;
          return { ...b, items: b.items.filter(i => i.id !== bqItem.id) };
        }));
      }
    } catch (err) {
      console.error('Blits question remove error:', err);
    }
  }, [blits]);

  // ── Rasm yuklash ──
  const uploadQuestionImage = useCallback(async (questionId, file, type = 'image') => {
    if (!file) return null;
    try {
      const fieldName = 'file';
      const url = type === 'explanation_image' 
        ? `/manage/questions/${questionId}/explanation-image/`
        : `/manage/questions/${questionId}/${type}/`;
        
      const result = await uploadFile(url, file, fieldName);
      
      setQuestions(prev => prev.map(q => {
        if (q.id === questionId) {
          if (type === 'explanation_image') return { ...q, explanation_image: result.explanation_image };
          if (type === 'audio') return { ...q, audio: result.audio };
          return { ...q, image: result.image };
        }
        return q;
      }));
      
      return type === 'explanation_image' ? result.explanation_image : result.image;
    } catch (err) {
      console.error('❌ Failed to upload image:', err);
      return null;
    }
  }, []);

  const uploadExplanationImage = useCallback(async (questionId, file) => {
    if (!file) return null;
    try {
      const result = await uploadFile(`/manage/questions/${questionId}/explanation-image/`, file, 'file');
      setQuestions(prev => prev.map(q =>
        q.id === questionId ? { ...q, explanation_image: result.explanation_image } : q
      ));
      return result.explanation_image;
    } catch (err) {
      console.error('Izoh rasmi yuklashda xatolik:', err);
      return null;
    }
  }, []);

  // ── Eksport rasmlar ──
  const exportAllQuestionImages = useCallback(async () => {
    const sortedQuestions = [...questions].sort((a, b) => b.id - a.id).slice(0, 50);
    const questionsWithImages = sortedQuestions.filter(q => q.image || q.explanation_image);

    if (questionsWithImages.length === 0) {
      alert(t('noImagesToExport'));
      return;
    }

    const zip = new JSZip();
    let exportedCount = 0;

    for (const q of questionsWithImages) {
      if (q.image) {
        try {
          const response = await fetch(`/media/${q.image}`);
          if (response.ok) {
            const blob = await response.blob();
            const fileName = q.image.split('/').pop();
            zip.file(fileName, blob);
            exportedCount += 1;
          }
        } catch (error) {
          console.warn('Image export skipped:', q.id, error);
        }
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
    a.download = 'question_images.zip';
    a.click();
    URL.revokeObjectURL(url);
    alert(`${t('imagesExported')}: ${exportedCount}`);
  }, [questions, t]);

  const exportDescriptionImages = useCallback(async () => {
    const questionsWithDescImages = questions.filter(q => q.explanation_image);
    if (questionsWithDescImages.length === 0) {
      alert("Izoh rasmlari yo'q");
      return;
    }

    const zip = new JSZip();
    let exportedCount = 0;

    for (const q of questionsWithDescImages) {
      try {
        const response = await fetch(`/media/${q.explanation_image}`);
        if (response.ok) {
          const blob = await response.blob();
          const fileName = q.explanation_image.split('/').pop();
          zip.file(fileName, blob);
          exportedCount += 1;
        }
      } catch (error) {
        console.warn('Explanation image skipped:', q.id, error);
      }
    }

    if (exportedCount === 0) {
      alert("Hech narsa eksport qilinmadi");
      return;
    }

    const zipBlob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(zipBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'explanation_images.zip';
    a.click();
    URL.revokeObjectURL(url);
    alert(`Izoh rasmlari eksport qilindi: ${exportedCount}`);
  }, [questions]);

  const value = {
    sections, lessons, questions, answers, blits, loading,
    lang, setLang, t, getVal,
    loadData,
    updateSection, addSection, deleteSection,
    getLessonsBySection, updateLesson, addLesson, deleteLesson, reorderLessons,
    getQuestionsByLesson, getQuestionById, updateQuestion, addQuestion, deleteQuestion, reorderQuestions,
    getAnswersByQuestion, updateAnswer, addAnswer, deleteAnswer,
    updateBlits, addBlits, deleteBlits, addQuestionToBlits, removeQuestionFromBlits,
    exportAllQuestionImages, exportDescriptionImages, uploadQuestionImage, uploadExplanationImage,
  };

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error('useData must be used within DataProvider');
  return ctx;
}
