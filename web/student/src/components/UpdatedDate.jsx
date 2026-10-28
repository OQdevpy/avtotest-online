import { useEffect, useState } from 'react';
import { useCustomContext } from '../context/TestContext';
import { getContentInfo, onContentInfo } from '../utils/dataLoader';

// Kontent versiyasi — oxirgi marta savol qo'shilgan/tahrirlangan sana, har bir
// sahifada navbar'da, til tanlashning chap tomonida. Masalan: "version: 26.11.26"
const TITLE = { uz: 'Oxirgi yangilanish', cry: 'Охирги янгиланиш', ru: 'Последнее обновление' };

// Sana Toshkent vaqti bo'yicha (kompyuter soat mintaqasidan qat'i nazar)
export function formatUpdatedDate(iso) {
    if (!iso) return '';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '';
    const parts = Object.fromEntries(
        new Intl.DateTimeFormat('en-US', {
            timeZone: 'Asia/Tashkent', day: '2-digit', month: '2-digit', year: '2-digit',
        }).formatToParts(date).map((p) => [p.type, p.value]),
    );
    return `version: ${parts.day}.${parts.month}.${parts.year}`;
}

function UpdatedDate() {
    const { lang } = useCustomContext();
    const [updatedAt, setUpdatedAt] = useState(getContentInfo().updated_at);

    useEffect(() => onContentInfo((info) => setUpdatedAt(info.updated_at)), []);

    const text = formatUpdatedDate(updatedAt);
    if (!text) return null;
    return (
        <div className="flex items-center h-10 px-3 text-white font-semibold whitespace-nowrap"
            title={TITLE[lang] || TITLE.uz}>
            {text}
        </div>
    );
}

export default UpdatedDate;
