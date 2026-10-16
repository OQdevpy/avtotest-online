import { useEffect, useState } from 'react';
import { useCustomContext } from '../context/TestContext';
import { getContentInfo, onContentInfo } from '../utils/dataLoader';

// Oxirgi marta savol qo'shilgan/tahrirlangan sana — bosh sahifada, til
// tanlashning chap tomonida. Masalan: "26-noyabr 2026-y."
const MONTHS = {
    uz: ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust',
        'sentabr', 'oktabr', 'noyabr', 'dekabr'],
    cry: ['январ', 'феврал', 'март', 'апрел', 'май', 'июн', 'июл', 'август',
        'сентабр', 'октабр', 'ноябр', 'декабр'],
    ru: ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
        'сентября', 'октября', 'ноября', 'декабря'],
};
const TITLE = { uz: 'Oxirgi yangilanish', cry: 'Охирги янгиланиш', ru: 'Последнее обновление' };

// Sana Toshkent vaqti bo'yicha (kompyuter soat mintaqasidan qat'i nazar)
export function formatUpdatedDate(iso, lang) {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    const parts = Object.fromEntries(
        new Intl.DateTimeFormat('en-US', {
            timeZone: 'Asia/Tashkent', day: 'numeric', month: 'numeric', year: 'numeric',
        }).formatToParts(date).map((p) => [p.type, p.value]),
    );
    const month = (MONTHS[lang] || MONTHS.uz)[Number(parts.month) - 1];
    if (lang === 'ru') return `${parts.day} ${month} ${parts.year} г.`;
    if (lang === 'cry') return `${parts.day}-${month} ${parts.year}-й.`;
    return `${parts.day}-${month} ${parts.year}-y.`;
}

function UpdatedDate() {
    const { lang } = useCustomContext();
    const [updatedAt, setUpdatedAt] = useState(getContentInfo().updated_at);

    useEffect(() => onContentInfo((info) => setUpdatedAt(info.updated_at)), []);

    const text = formatUpdatedDate(updatedAt, lang);
    if (!text) return null;
    return (
        <div className="flex items-center h-10 px-3 text-white font-semibold whitespace-nowrap"
            title={TITLE[lang] || TITLE.uz}>
            {text}
        </div>
    );
}

export default UpdatedDate;
