/**
 * Ma'lumot yuklovchi — yagona backend (avtotest-online) API'sidan.
 *
 * Seoul'dagi dataLoader bilan bir xil nomlar va bir xil shakl eksport qilinadi
 * (oraliq_db, oraliqdarslar_db, oraliqdarslarquestion_db, ...), shuning uchun
 * sahifa va komponentlar o'zgarmaydi. Farqi: ma'lumot db.enc / lokal JSON'dan
 * emas, kirilgandan keyin API'dan bir marta olinadi (`loadAllData`) va shu
 * massivlar/obyektlar joyida to'ldiriladi.
 *
 * Savollar `mode=study` bilan olinadi — testlar javobni mijozda tekshiradi.
 * Rasm yo'llari nisbiy (`images/x.webp`), `media_path` ga ulanadi.
 */

import { API_LANG, apiFetch, fetchAllPages } from '../api/client';

// ── Eksportlar (seoul bilan bir xil) ─────────────────────────────────────────
export const oraliq_db = [];
export const oraliqdarslar_db = [];
export const oraliqdarslarquestion_db = [];
export const oraliqdarslaranswer_db = [];

export const question_db = [];
export const answer_db = oraliqdarslaranswer_db;
export const image_db = [];
export const student_db = [];
export const test_db = [];

export const blits_db = [];
export const blits_questions_db = {};

// ── Yordamchilar ────────────────────────────────────────────────────────────
const LANGS = Object.keys(API_LANG); // uz, ru, cry

function replaceAll(target, items) {
  target.splice(0, target.length, ...items);
}

// Faqat tanlangan tilda `name` qaytaradigan ro'yxatni uch tilda olib,
// `name_uz/name_ru/name_cry` ga birlashtiradi.
async function fetchNamedList(path) {
  const lists = await Promise.all(
    LANGS.map((lang) => fetchAllPages(path, { lang: API_LANG[lang] })),
  );
  const [base, ...others] = lists;
  return base.map((item) => {
    const merged = { ...item, name_uz: item.name };
    others.forEach((list, i) => {
      const same = list.find((other) => other.id === item.id);
      merged[`name_${LANGS[i + 1]}`] = same ? same.name : item.name;
    });
    return merged;
  });
}

// Bir vaqtda `limit` tadan ko'p so'rov yubormaslik uchun
async function mapLimited(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index], index);
    }
  });
  await Promise.all(workers);
  return results;
}

// ── Yuklash ─────────────────────────────────────────────────────────────────
let loadPromise = null;
let loaded = false;

export function isDataLoaded() {
  return loaded;
}

export function resetData() {
  loaded = false;
  loadPromise = null;
}

async function loadAll() {
  const [sections, lessons, questions, tickets, blits] = await Promise.all([
    fetchNamedList('/sections/'),
    fetchNamedList('/lessons/'),
    fetchAllPages('/questions/', { mode: 'study' }),
    fetchAllPages('/tickets/'),
    fetchNamedList('/blits/'),
  ]);

  replaceAll(oraliq_db, sections.map((s) => ({
    id: s.id, name_uz: s.name_uz, name_ru: s.name_ru, name_cry: s.name_cry, tartib: s.order,
  })));

  replaceAll(oraliqdarslar_db, lessons.map((l) => ({
    id: l.id, oraliq: l.section_id,
    name_uz: l.name_uz, name_ru: l.name_ru, name_cry: l.name_cry, tartib: l.order,
  })));

  const questionRows = questions.map((q) => ({
    id: q.id, oraliq_dars: q.lesson_id,
    question_uz: q.question_uz, question_ru: q.question_ru, question_cry: q.question_cry,
    image: q.image || '', description_image: q.explanation_image || null,
    tartib: q.order, is_in_web: true,
  }));
  replaceAll(oraliqdarslarquestion_db, questionRows);

  replaceAll(oraliqdarslaranswer_db, questions.flatMap((q) =>
    [...(q.answers || [])]
      .sort((a, b) => (a.order || 0) - (b.order || 0))
      .map((a) => ({
        id: a.id, oraliq_dars_question: q.id,
        answer_uz: a.answer_uz, answer_ru: a.answer_ru, answer_cry: a.answer_cry, is_true: a.is_true,
      })),
  ));

  const byId = new Map(questionRows.map((q) => [q.id, q]));

  // Variantlar = biletlar (1-bilet → var_id 0, seoul'dagi indekslash bilan bir xil)
  const sortedTickets = [...tickets].sort((a, b) => a.number - b.number);
  const ticketQuestionIds = await mapLimited(sortedTickets, 6, async (ticket) => {
    const detail = await apiFetch(`/tickets/${ticket.number}/`, { query: { mode: 'study' } });
    return (detail.questions || []).map((q) => q.id);
  });
  replaceAll(question_db, sortedTickets.map((ticket, index) => ({
    var_id: index,
    data: ticketQuestionIds[index]
      .map((id) => byId.get(id))
      .filter(Boolean)
      .map((q) => ({ ...q, var_id: index })),
  })));

  // Blits
  const blitsQuestionIds = await mapLimited(blits, 4, async (b) => {
    const detail = await apiFetch(`/blits/${b.id}/`, { query: { mode: 'study' } });
    return (detail.questions || []).map((q) => q.id);
  });
  replaceAll(blits_db, blits.map((b, i) => ({
    id: b.id, name_uz: b.name_uz, name_ru: b.name_ru, name_cry: b.name_cry,
    tartib: b.order, question_ids: blitsQuestionIds[i],
  })));
  Object.keys(blits_questions_db).forEach((key) => delete blits_questions_db[key]);
  blits_db.forEach((b) => {
    blits_questions_db[b.id] = b.question_ids.map((id) => byId.get(id)).filter(Boolean);
  });

  loaded = true;
}

export function loadAllData() {
  if (!loadPromise) {
    loadPromise = loadAll().catch((error) => {
      loadPromise = null;
      throw error;
    });
  }
  return loadPromise;
}

export default {
  oraliq: oraliq_db,
  oraliqdarslar: oraliqdarslar_db,
  oraliqdarslarquestion: oraliqdarslarquestion_db,
  oraliqdarslaranswer: oraliqdarslaranswer_db,
  question: question_db,
  answer: answer_db,
  blits: blits_db,
  blits_questions: blits_questions_db,
};
