// Kontentni API'dan olib, komponentlar kutgan eski ko'rinishga keltiradi:
// `name_uz/ru/cry`, `question_*` / `answer_*` (compat), `tartib`,
// `lesson_name`, to'liq `image` URL.
//
// Savollar doim `mode=study` bilan olinadi: testlar javobni mijozda
// tekshiradi, shuning uchun `is_true` kerak.

import { API_LANG, apiFetch, fetchAllPages } from './client';

const LANGS = Object.keys(API_LANG); // uz, ru, cry

// Faqat tanlangan tilda `name` qaytaradigan ro'yxatni uch tilda olib,
// `name_uz/name_ru/name_cry` ga birlashtiradi.
async function fetchAllLangs(path, query = {}, fetcher = (p, q) => apiFetch(p, { query: q })) {
    const lists = await Promise.all(
        LANGS.map((lang) => fetcher(path, { ...query, lang: API_LANG[lang] })),
    );
    const unwrap = (data) => (Array.isArray(data) ? data : data.results);
    const [base, ...others] = lists.map(unwrap);
    return base.map((item) => {
        const merged = { ...item, tartib: item.order, name_uz: item.name };
        others.forEach((list, i) => {
            const same = list.find((other) => other.id === item.id);
            merged[`name_${LANGS[i + 1]}`] = same ? same.name : item.name;
        });
        return merged;
    });
}

export const fetchSections = () => fetchAllLangs('/sections/');

export const fetchLessons = (section) => fetchAllLangs('/lessons/', { section });

export const fetchBlitsList = () => fetchAllLangs('/blits/', {}, fetchAllPages);

// Dars id → "<bo'lim tartibi>.<dars nomi>" (uch tilda). Bir marta olinadi.
let lessonNamesPromise = null;
function lessonNames() {
    if (!lessonNamesPromise) {
        lessonNamesPromise = Promise.all([fetchSections(), fetchLessons()])
            .then(([sections, lessons]) => {
                const sectionOrder = Object.fromEntries(sections.map((s) => [s.id, s.order]));
                return Object.fromEntries(lessons.map((lesson) => {
                    const prefix = sectionOrder[lesson.section_id];
                    const name = (lang) => (prefix ? `${prefix}.${lesson[`name_${lang}`]}` : lesson[`name_${lang}`]);
                    return [lesson.id, { name_uz: name('uz'), name_ru: name('ru'), name_cry: name('cry') }];
                }));
            })
            .catch((err) => {
                lessonNamesPromise = null;
                throw err;
            });
    }
    return lessonNamesPromise;
}

export function resetContentCache() {
    lessonNamesPromise = null;
}

function shuffle(array) {
    const copy = [...array];
    for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
}

async function normalizeQuestions(questions, { shuffleAnswers = false } = {}) {
    const names = await lessonNames();
    return questions.map((q) => {
        const answers = [...(q.answers || [])].sort((a, b) => a.order - b.order);
        return {
            ...q,
            image: q.image_url || '',
            lesson_name: names[q.lesson_id] || { name_uz: '', name_ru: '', name_cry: '' },
            answers: shuffleAnswers ? shuffle(answers) : answers,
        };
    });
}

// Dars savollari (o'rganish ekrani)
export async function fetchLessonQuestions(lesson) {
    const questions = await fetchAllPages('/questions/', { lesson, mode: 'study' });
    return normalizeQuestions(questions);
}

// Bo'limdan tasodifiy `count` ta savol (oraliq test)
export async function fetchSectionTest(section, count) {
    const questions = await fetchAllPages('/questions/', { section, mode: 'study' });
    return normalizeQuestions(shuffle(questions).slice(0, Number(count)), { shuffleAnswers: true });
}

// Barcha savollardan tasodifiy 20 yoki 50 ta (imtihon)
export async function fetchRandomTest(count) {
    const data = await apiFetch('/exam/generate/', { query: { count, mode: 'study' } });
    return normalizeQuestions(shuffle(data.questions), { shuffleAnswers: true });
}

export async function fetchTickets() {
    return fetchAllPages('/tickets/');
}

export async function fetchTicketQuestions(number) {
    const data = await apiFetch(`/tickets/${number}/`, { query: { mode: 'study' } });
    return normalizeQuestions(data.questions);
}

export async function fetchBlitsQuestions(id) {
    const data = await apiFetch(`/blits/${id}/`, { query: { mode: 'study' } });
    return normalizeQuestions(shuffle(data.questions), { shuffleAnswers: true });
}
