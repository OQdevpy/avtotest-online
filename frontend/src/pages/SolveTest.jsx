import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";
import {
  oraliq_db, oraliqdarslar_db, oraliqdarslarquestion_db, oraliqdarslaranswer_db,
} from '../utils/dataLoader';

function SolveTest() {
    const { count } = useParams();

    const { Background } = useCustomContext();
    const [solveTest, setSolveTest] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchSolveTest = useCallback(async (count) => {
        try {
            setLoading(true);
            setError(null);

            const countAsNumber = Number(count);

            // ═══════════════════════════════════════════════════════════
            // STRATIFIED + SPACING ALGORITHM
            // ═══════════════════════════════════════════════════════════

            // 1. Bo'limlar bo'yicha savollarni guruhlash
            const questionsBySection = {};
            oraliq_db.forEach(section => {
                const sectionLessons = oraliqdarslar_db.filter(l => l.oraliq === section.id);
                const lessonIds = sectionLessons.map(l => l.id);
                const sectionQuestions = oraliqdarslarquestion_db.filter(q =>
                    lessonIds.includes(q.oraliq_dars)
                );
                if (sectionQuestions.length > 0) {
                    questionsBySection[section.id] = {
                        section,
                        questions: [...sectionQuestions].sort(() => Math.random() - 0.5),
                        lessonIds
                    };
                }
            });

            // 2. Proporsional taqsimot hisoblash
            const totalQuestions = oraliqdarslarquestion_db.length;
            const sectionIds = Object.keys(questionsBySection);
            const quotas = {};

            sectionIds.forEach(sectionId => {
                const sectionCount = questionsBySection[sectionId].questions.length;
                // Proporsional kvota (kamida 1 ta)
                quotas[sectionId] = Math.max(1, Math.round((sectionCount / totalQuestions) * countAsNumber));
            });

            // Kvotalarni countAsNumber ga moslash
            let totalQuota = Object.values(quotas).reduce((a, b) => a + b, 0);
            while (totalQuota > countAsNumber) {
                // Eng ko'p kvotali bo'limdan kamaytirish
                const maxSection = sectionIds.reduce((a, b) => quotas[a] > quotas[b] ? a : b);
                if (quotas[maxSection] > 1) {
                    quotas[maxSection]--;
                    totalQuota--;
                } else break;
            }
            while (totalQuota < countAsNumber) {
                // Savollar ko'p bo'limga qo'shish
                const maxQSection = sectionIds.reduce((a, b) =>
                    questionsBySection[a].questions.length > questionsBySection[b].questions.length ? a : b
                );
                quotas[maxQSection]++;
                totalQuota++;
            }

            // 3. Har bo'limdan kvota bo'yicha savollar olish
            const selectedBySection = {};
            sectionIds.forEach(sectionId => {
                const available = questionsBySection[sectionId].questions;
                const quota = Math.min(quotas[sectionId], available.length);
                selectedBySection[sectionId] = available.slice(0, quota).map(q => ({
                    ...q,
                    _sectionId: Number(sectionId)
                }));
            });

            // 4. Spacing bilan birlashtirish
            const finalQuestions = [];
            const MIN_SECTION_SPACING = 2; // Bir bo'limdan keyingi savol uchun minimal oraliq
            const MIN_LESSON_SPACING = 3;  // Bir mavzudan keyingi savol uchun minimal oraliq

            let iterations = 0;
            const maxIterations = countAsNumber * 20;

            while (finalQuestions.length < countAsNumber && iterations < maxIterations) {
                iterations++;

                // Bo'limlarni shuffle
                const shuffledSections = [...sectionIds].sort(() => Math.random() - 0.5);

                for (const sectionId of shuffledSections) {
                    if (finalQuestions.length >= countAsNumber) break;

                    const sectionQuestions = selectedBySection[sectionId];
                    if (!sectionQuestions || sectionQuestions.length === 0) continue;

                    // Spacing tekshirish - bo'lim
                    const recentSections = finalQuestions
                        .slice(-MIN_SECTION_SPACING)
                        .map(q => q._sectionId);
                    if (recentSections.includes(Number(sectionId))) continue;

                    // Spacing tekshirish - mavzu
                    const recentLessons = finalQuestions
                        .slice(-MIN_LESSON_SPACING)
                        .map(q => q.oraliq_dars);

                    // Mavzusi yaqinda uchramagan savolni topish
                    const validIndex = sectionQuestions.findIndex(q =>
                        !recentLessons.includes(q.oraliq_dars)
                    );

                    if (validIndex !== -1) {
                        finalQuestions.push(sectionQuestions.splice(validIndex, 1)[0]);
                    }
                }
            }

            // 5. Agar yetarli bo'lmasa, qolganlarini qo'shish
            if (finalQuestions.length < countAsNumber) {
                const selectedIds = new Set(finalQuestions.map(q => q.id));
                const remaining = oraliqdarslarquestion_db
                    .filter(q => !selectedIds.has(q.id))
                    .sort(() => Math.random() - 0.5);

                while (finalQuestions.length < countAsNumber && remaining.length > 0) {
                    const q = remaining.shift();
                    const lesson = oraliqdarslar_db.find(l => l.id === q.oraliq_dars);
                    finalQuestions.push({
                        ...q,
                        _sectionId: lesson?.oraliq
                    });
                }
            }

            // 6. Javoblar va mavzu nomlarini qo'shish
            finalQuestions.forEach(item => {
                item.answers = oraliqdarslaranswer_db
                    .filter(a => a.oraliq_dars_question === item.id)
                    .sort(() => Math.random() - 0.5);
                const lesson = oraliqdarslar_db.find(l => l.id === item.oraliq_dars);
                const oraliq = oraliq_db.find(o => o.id === lesson?.oraliq);
                item.lesson_name = {
                    "name_ru": `${oraliq?.tartib || ''}.${lesson?.name_ru || ''}`,
                    "name_uz": `${oraliq?.tartib || ''}.${lesson?.name_uz || ''}`,
                    "name_cry": `${oraliq?.tartib || ''}.${lesson?.name_cry || ''}`,
                };
                // Ichki field larni tozalash
                delete item._sectionId;
            });

            setSolveTest([...finalQuestions]);
        } catch (err) {
            console.error('Fetch error:', err);
            setError('Failed to fetch quiz data');
        } finally {
            setLoading(false);
        }
    }, []);
    
        // Use effect to fetch data when the component mounts
        useEffect(() => {
            fetchSolveTest(count);
        }, [fetchSolveTest]);  // Dependency array includes fetchSolveTest
        
        // Conditional rendering based on loading or error states
        if (count==20 && solveTest.length==50 || count == 50 && solveTest.length==20 ) return null
        if (loading) return <p>Loading...</p>;
        if (error) return <p>{error}</p>;
        if (!solveTest || solveTest.length === 0) return <p>No data available</p>;
    



    const time = count === '20' ? true : false;




    if (!solveTest || solveTest == undefined) return null;


    return (
        <div
            style={{
                backgroundImage: `url(${Background})`,
                backgroundSize: 'cover',  // Ensures the image covers the entire container
                backgroundRepeat: 'no-repeat',  // Prevents the image from repeating
                backgroundAttachment: 'fixed',  // Keeps the background image fixed when scrolling
                height: '100vh',  // Ensure the container takes full viewport height
                margin: 0,  // Remove default margin
                padding: 0,  // Remove default padding
                overflow: 'hidden'  // Prevent overflow
            }}>
            <Navbar />
            <div
                className="bg-gray-950/90 max-w-full min-h-full"
                style={{
                    // margin: '1rem', // Removed unnecessary margin
                    // marginBottom: '0.5rem',
                }}
            >
                {
                    time ? <SolveQuizComponent data={solveTest} /> : <SolveQuizComponentWithoutTime data={solveTest} />
                }
                <Outlet />
            </div>
        </div>
    )
}

export default SolveTest;
