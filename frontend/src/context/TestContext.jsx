import { createContext, useCallback, useContext, useEffect, useState } from 'react';

// Barcha ma'lumot — yagona backend API'sidan (utils/dataLoader.js)
import {
  oraliq_db,
  oraliqdarslar_db,
  oraliqdarslarquestion_db,
  oraliqdarslaranswer_db,
  question_db,
  answer_db,
} from '../utils/dataLoader';


const TestContext = createContext(null);
const ContextProvider = ({ children }) => {
    const [active, setActive] = useState(true);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // Rasm/izoh rasmi: backend media manzili + nisbiy yo'l (`images/x.webp`)
    const media_path = `${(import.meta.env.VITE_MEDIA_BASE_URL || '').replace(/\/+$/, '')}/media/`;

    // Fon va logo — ilova ichidagi statik rasmlar
    const DefaultImge = './static-images/default_image.jpg'
    const Background = './static-images/romo-sagan-thumb.jpg'
    const bgLogo = './static-images/removebg.png'

    const decodeData = (encodedData, id) => {
        const combinedData = atob(encodedData);

        const firstEncodedData = combinedData.slice(0, id) + combinedData.slice(id + id);

        const decodedData = atob(firstEncodedData);

        return decodedData;
    };



    //variants
    const [variants, setVariants] = useState(null);
    const fetchVariants = async () => {
        const count = question_db.length; // Calculate chunks
        let data = [];

        for (let i = 0; i < count; i++) {
            // Create a variant object for each index
            const variant = {
                name_uz: `${i + 1}-variant`, // Translation for Uzbek
                name_ru: `${i + 1}-вариант`, // Translation for Russian
                name_cry: `${i + 1}-вариант`, // Translation for Cyrillic
                // Add any other properties you need, or keep it as it is
            };

            data.push(variant); // Add the variant to the data array
        }

        setVariants(data); // Set the state with the generated data
        setLoading(false); // Finish loading
    };


    const [variant, setVariant] = useState(null);

    const fetchVariant = async (index) => {
        // Find the item in question_db with the specified var_id
        const data = question_db.find(item => item.var_id == index).data;

        if (data) {
            data.forEach(item =>
                item.answers = answer_db.filter(new_item => new_item.oraliq_dars_question === item.id))

            setVariant(data); // Set the filtered data
        } else {
            console.error("No variant found with var_id:", index);
        }


        setLoading(false); // Finish loading
    };



    // random tests 

    const [randomTests, setRandomTests] = useState(null);
    const fetchRandomTests = async () => {
        const picked = [...oraliqdarslarquestion_db].sort(() => Math.random() - 0.5).slice(0, 20);
        picked.forEach(item => {
            item.answers = oraliqdarslaranswer_db.filter((new_item) => new_item.oraliq_dars_question === item.id);
        });
        setRandomTests(picked);
        setLoading(false);
    }


    const [oraliq, setOraliq] = useState([]);
    const fetchOraliq = async () => {

        setOraliq(oraliq_db);
        setLoading(false);

    }

    const [lessons, setLessons] = useState([]);
    const fetchLessons = async (index) => {
        const data = oraliqdarslar_db
            .filter((item) => item['oraliq'] == index)
            .sort((a, b) => (a.tartib || 0) - (b.tartib || 0));
        setLessons(data);
    }



    const [oraliqTest, setOraliqTest] = useState([]);
    const fetchOraliqTest = useCallback(async (index, count) => {
        setLoading(true);
        const oraliq = oraliq_db.find((item) => item.id == index);


        const lessons = oraliqdarslar_db.filter((item) => item['oraliq'] == index);

        const lessonIds = lessons.map(item => item.id); // Extract IDs

        const filteredQuestions = oraliqdarslarquestion_db.filter((item) => {
            return lessonIds.some(lessonId => lessonId === item.oraliq_dars);
        });


        const shuffledQuestions = filteredQuestions.sort(() => Math.random() - 0.5); // Shuffle array
        const countAsNumber = Number(count); // Ensure count is a number
        const randomQuestions = shuffledQuestions.slice(0, countAsNumber); // Select the first 'count' questions

        // Assign answers to the selected random questions
        randomQuestions.forEach(item => {
            item.answers = oraliqdarslaranswer_db.filter((new_item) => new_item.oraliq_dars_question === item.id);
            const lesson = oraliqdarslar_db.find((new_item) => new_item.id === item.oraliq_dars);
            item.lesson_name = {
                "name_ru": oraliq.tartib + '.' + lesson.name_ru,
                "name_uz": oraliq.tartib + '.' + lesson.name_uz,
                "name_cry": oraliq.tartib + '.' + lesson.name_cry
            }
        });


        setOraliqTest(randomQuestions);
        setLoading(false);
    }, []);


    const [solveTest, setSolveTest] = useState([]);

    const fetchSolveTest = useCallback(async (count) => {
        try {
            setLoading(true);  // Start loading
            setError(null);    // Reset error state

            // Shuffle questions and select based on count
            const shuffledQuestions = oraliqdarslarquestion_db.sort(() => Math.random() - 0.5);
            const countAsNumber = Number(count);
            const randomQuestions = shuffledQuestions.slice(0, countAsNumber);

            // Add answers and lesson names
            randomQuestions.forEach(item => {
                item.answers = oraliqdarslaranswer_db.filter((new_item) => new_item.oraliq_dars_question === item.id);
                const lesson = oraliqdarslar_db.find((new_item) => new_item.id === item.oraliq_dars);
                const oraliq = oraliq_db.find((new_item) => new_item.id === lesson.oraliq);
                item.lesson_name = {
                    "name_ru": `${oraliq.tartib}.${lesson.name_ru}`,
                    "name_uz": `${oraliq.tartib}.${lesson.name_uz}`,
                    "name_cry": `${oraliq.tartib}.${lesson.name_cry}`,
                };
            });

            // Use functional update to ensure the latest state is captured
            setSolveTest((prev) => [...randomQuestions]);
        } catch (err) {
            setError('Failed to fetch quiz data');
        } finally {
            setLoading(false);  // Stop loading
        }
    }, []);

    const [oraliqLessontest, setOraliqLessonTest] = useState([]);
    const fetchOraliqLessonTest = async (index) => {
        const oraliq_dars = oraliqdarslar_db.find((item) => item.id == index);
        const oraliq = oraliq_db.find((item) => item.id == oraliq_dars.oraliq);


        const data = oraliqdarslarquestion_db
            .filter((item) => {
                if (item.oraliq_dars == index) {
                    item.answers = oraliqdarslaranswer_db.filter((new_item) => new_item.oraliq_dars_question == item.id);
                    item.lesson_name = {
                        "name_ru": oraliq.tartib + '.' + oraliq_dars.name_ru,
                        "name_uz": oraliq.tartib + '.' + oraliq_dars.name_uz,
                        "name_cry": oraliq.tartib + '.' + oraliq_dars.name_cry
                    };
                    return item;
                }
            })
            .sort((a, b) => (a.tartib || 0) - (b.tartib || 0));
        setOraliqLessonTest(data);
    };

    // lang
    const [lang, setLang] = useState(localStorage.getItem('lang') || 'uz');
    const changeLang = (lang) => {
        setLang(lang);
        localStorage.setItem('lang', lang);
    }

    // get translation
    const [translations, setTranslations] = useState({});
    const data = {
        "return": {
            "ru": "Назад",
            "uz": "Ortga",
            "cry": "Ортга"
        },
        "login": {
            "ru": "Вход",
            "uz": "Kirish",
            "cry": "Кириш"
        },
        "logout": {
            "ru": "Выход",
            "uz": "Chiqish",
            "cry": "Чиқиш"
        },
        "exam": {
            "ru": "Экзамен",
            "uz": "Imtihon",
            "cry": "Имтиҳон"
        },
        "test": {
            "ru": "Тест",
            "uz": "Test",
            "cry": "Тест"
        },
        "time_end": {
            "ru": "Время истекло!",
            "uz": "Vaqt tugadi!",
            "cry": "Вақт тугади!"
        },
        "result": {
            "ru": "Результат: ",
            "uz": "Natija: ",
            "cry": "Натижа: "
        },
        "templates": {
            "ru": "Шаблоны",
            "uz": "Shablonlar",
            "cry": "Шаблонлар"
        },
        "dashboard": {
            "ru": "Главная",
            "uz": "Bosh sahifa",
            "cry": "Бош саҳифа"
        },
        "lessons": {
            "ru": "Уроки",
            "uz": "Darslar",
            "cry": "Дарслар"
        },
        "oraliqTest": {
            "ru": "Промежуточный тест",
            "uz": "Oraliq test",
            "cry": "Оралиқ тест"
        },
        "solveTest": {
            "ru": "Решить тест по теме",
            "uz": "Mavzu bo'yicha test ishlash",
            "cry": "Мавзу бўйича тест ишлаш"
        },
        "startZero": {
            "ru": "Начать сначала",
            "uz": "Boshidan boshlash",
            "cry": "Бошидан бошлаш"
        },
        "submitted": {
            "ru": "Сдан",
            "uz": "Topshirildi",
            "cry": "Топширилди"
        },
        "notSubmitted": {
            "ru": "Не сдан",
            "uz": "Topshrilmadi",
            "cry": "Топширилмади"
        },
        "variants": {
            "ru": "Варианты",
            "uz": "Variantlar",
            "cry": "Вариантлар"
        },
        "selectQuestionCount": {
            "ru": "Выберите количество вопросов",
            "uz": "Savollar sonini tanlang",
            "cry": "Саволлар сонини танланг"
        },
        "questions": {
            "ru": "вопросов",
            "uz": "ta savol",
            "cry": "та савол"
        },
        "cancel": {
            "ru": "Отмена",
            "uz": "Bekor qilish",
            "cry": "Бекор қилиш"
        },
    }


    useEffect(() => {
        const fetchTranslations = async () => {
            try {
                setTranslations(data);
            } catch (error) {
                console.error("Error fetching translations:", error);
            }
        };

        fetchTranslations();
    }, []);
    const getTranslation = (key) => {
        return translations[key] ? translations[key][lang] : key;
    };

    const getTranslationValue = (item, key) => {
        return lang == 'uz' ? item?.[key + '_uz'] : lang == 'cry' ? item?.[key + '_cry'] : item?.[key + '_ru']
    }


    const returnResult = (trueCount, questionCount) => {
        // Natijani hisoblash
        const percentage = (trueCount / questionCount) * 100;
        let resultText = 'notSubmitted';

        // 50 ta = max 4 xato (92%), boshqa = max 2 xato (90%)
        const passThreshold = questionCount === 50 ? 92 : 90;

        // Rangni belgilash
        let colorClass = 'text-red-600'; // default qizil
        if (percentage >= passThreshold) {
            colorClass = 'text-green-600'; // yashil
            resultText = 'submitted'
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
                // static-images
                DefaultImge,
                bgLogo,
                Background,
                media_path,


                active,
                setActive,
                variants,
                fetchVariants,
                fetchVariant,
                variant,
                randomTests,
                fetchRandomTests,

                oraliq,
                fetchOraliq,

                lessons,
                fetchLessons,

                oraliqLessontest,
                fetchOraliqLessonTest,

                oraliqTest,
                fetchOraliqTest,

                solveTest,
                setSolveTest,
                fetchSolveTest,

                lang,
                changeLang,
                getTranslation,
                getTranslationValue,
                loading,
                decodeData,

                returnResult
            }}
        >
            {children}
        </TestContext.Provider>
    )
}

const useCustomContext = () => useContext(TestContext)

export { ContextProvider, useCustomContext }
