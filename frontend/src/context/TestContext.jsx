import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';

const TestContext = createContext(null);
const ContextProvider = ({ children }) => {
    const [active, setActive] = useState(true);
    const [loading, setLoading] = useState(true);
    const URL = import.meta.env.VITE_API_URL;
    const media_path = import.meta.env.VITE_MEDIA_BASE_URL;

    const DefaultImge = './static-images/default_image.jpg';
    const Background = './static-images/romo-sagan-thumb.jpg';
    const bgLogo = './static-images/removebg.png';

    const decodeData = (encodedData, id) => {
        const combinedData = atob(encodedData);
        const firstEncodedData = combinedData.slice(0, id) + combinedData.slice(id + id);
        const decodedData = atob(firstEncodedData);
        return decodedData;
    };

    const [variants, setVariants] = useState(null);
    const fetchVariants = async () => {
        try {
            const res = await fetch(`${URL}/tickets/?token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            const mapped = data.map(t => ({
                id: t.number,
                name_uz: `${t.number}-variant`,
                name_ru: `${t.number}-вариант`,
                name_cry: `${t.number}-вариант`,
            }));
            setVariants(mapped);
        } catch(e) { console.error(e); }
        setLoading(false);
    };

    const [variant, setVariant] = useState(null);
    const fetchVariant = async (index) => {
        try {
            const res = await fetch(`${URL}/tickets/${parseInt(index) + 1}/?token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setVariant(data.questions);
        } catch(e) { console.error(e); }
        setLoading(false);
    };

    const [randomTests, setRandomTests] = useState(null);
    const fetchRandomTests = async () => {
        try {
            const res = await fetch(`${URL}/random-test/?token=${localStorage.getItem('quizToken')}`);
            if (res.status === 403) {
                localStorage.removeItem('quizToken');
                window.location.href = "/login";
            }
            const data = await res.json();
            setRandomTests(data);
        } catch(e) { console.error(e); }
        setLoading(false);
    }

    const [oraliq, setOraliq] = useState([]);
    const fetchOraliq = async () => {
        try {
            const res = await fetch(`${URL}/sections/?token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setOraliq(data);
        } catch(e) { console.error(e); }
        setLoading(false);
    }

    const [lessons, setLessons] = useState([]);
    const fetchLessons = async (index) => {
        try {
            const res = await fetch(`${URL}/lessons/?section=${index}&token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setLessons(data);
        } catch(e) { console.error(e); }
    }

    const [oraliqTest, setOraliqTest] = useState([]);
    const fetchOraliqTest = useCallback(async (index, count) => {
        setLoading(true);
        try {
            const res = await fetch(`${URL}/random-questions/?section=${index}&count=${count}&token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setOraliqTest(data);
        } catch(e) { console.error(e); }
        setLoading(false);
    }, [URL]);

    const [solveTest, setSolveTest] = useState([]);
    const fetchSolveTest = useCallback(async (count) => {
        setLoading(true);
        try {
            const res = await fetch(`${URL}/random-questions/?count=${count}&token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setSolveTest(data);
        } catch(e) { console.error(e); }
        setLoading(false);
    }, [URL]);

    const [oraliqLessontest, setOraliqLessonTest] = useState([]);
    const fetchOraliqLessonTest = async (index) => {
        try {
            const res = await fetch(`${URL}/questions/?lesson=${index}&token=${localStorage.getItem('quizToken')}`);
            const data = await res.json();
            setOraliqLessonTest(data);
        } catch(e) { console.error(e); }
    };

    const [lang, setLang] = useState(localStorage.getItem('lang') || 'uz');
    const changeLang = (lang) => {
        setLang(lang);
        localStorage.setItem('lang', lang);
    }

    const [translations, setTranslations] = useState({});
    const translationData = {
        "return": { "ru": "Назад", "uz": "Ortga", "cry": "Ортга" },
        "login": { "ru": "Вход", "uz": "Kirish", "cry": "Кириш" },
        "logout": { "ru": "Выход", "uz": "Chiqish", "cry": "Чиқиш" },
        "exam": { "ru": "Экзамен", "uz": "Imtihon", "cry": "Имтиҳон" },
        "test": { "ru": "Тест", "uz": "Test", "cry": "Тест" },
        "time_end": { "ru": "Время истекло!", "uz": "Vaqt tugadi!", "cry": "Вақт тугади!" },
        "result": { "ru": "Результат: ", "uz": "Natija: ", "cry": "Натижа: " },
        "templates": { "ru": "Шаблоны", "uz": "Shablonlar", "cry": "Шаблонлар" },
        "dashboard": { "ru": "Главная", "uz": "Bosh sahifa", "cry": "Бош саҳифа" },
        "lessons": { "ru": "Уроки", "uz": "Darslar", "cry": "Дарслар" },
        "oraliqTest": { "ru": "Промежуточный тест", "uz": "Oraliq test", "cry": "Оралиq тест" },
        "solveTest": { "ru": "Решить тест по теме", "uz": "Mavzu bo'yicha test ishlash", "cry": "Мавзу бўйича тест ишлаш" },
        "startZero": { "ru": "Начать сначала", "uz": "Boshidan boshlash", "cry": "Бошидан бошлаш" },
        "submitted": { "ru": "Сдан", "uz": "Topshirildi", "cry": "Топширилди" },
        "notSubmitted": { "ru": "Не сдан", "uz": "Topshrilmadi", "cry": "Топширилмади" },
        "variants": { "ru": "Варианты", "uz": "Variantlar", "cry": "Вариантлар" }
    };

    useEffect(() => {
        setTranslations(translationData);
    }, []);

    const getTranslation = (key) => translations[key] ? translations[key][lang] : key;
    const getTranslationValue = (item, key) => lang === 'uz' ? item?.[key + '_uz'] : lang === 'cry' ? item?.[key + '_cry'] : item?.[key + '_ru'];

    const returnResult = (trueCount, questionCount) => {
        const percentage = (trueCount / questionCount) * 100;
        let resultText = 'notSubmitted';
        let colorClass = 'text-red-600';
        if (percentage >= 90) {
            colorClass = 'text-green-600';
            resultText = 'submitted';
        }
        return (
            <div className={`text-3xl font-bold text-center ${colorClass}`}>
                {`${getTranslation(resultText)}: ${percentage.toFixed(2)}%`}
            </div>
        );
    }

    return (
        <TestContext.Provider
            value={{
                DefaultImge, bgLogo, Background, media_path,
                active, setActive, variants, fetchVariants, fetchVariant, variant,
                randomTests, fetchRandomTests, oraliq, fetchOraliq, lessons, fetchLessons,
                oraliqLessontest, fetchOraliqLessonTest, oraliqTest, fetchOraliqTest,
                solveTest, setSolveTest, fetchSolveTest,
                lang, changeLang, getTranslation, getTranslationValue, loading, decodeData, returnResult
            }}
        >
            {children}
        </TestContext.Provider>
    )
}
const useCustomContext = () => useContext(TestContext);
export { ContextProvider, useCustomContext };
