import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import {
  oraliq_db, oraliqdarslar_db, oraliqdarslarquestion_db, oraliqdarslaranswer_db,
} from '../utils/dataLoader';

function SolveOraliqTest() {
    const { count, id } = useParams();
    const { Background } = useCustomContext();
    const [OraliqTest,setOraliqTest] = useState([])


    const fetchOraliqTest =  useCallback( async (index, count) => {
        const oraliq = oraliq_db.find((item) => item.id == index);
        const lessons = oraliqdarslar_db.filter((item) => item['oraliq'] == index);
        const lessonIds = lessons.map(item => item.id);

        // Savollarni mavzular bo'yicha guruhlash
        const questionsByLesson = {};
        lessonIds.forEach(lessonId => {
            questionsByLesson[lessonId] = oraliqdarslarquestion_db
                .filter(q => q.oraliq_dars === lessonId)
                .sort(() => Math.random() - 0.5); // Har guruh ichida shuffle
        });

        const countAsNumber = Number(count);
        const selectedQuestions = [];
        const MIN_SPACING = 2; // Bir mavzudan keyingi savol uchun minimal oraliq

        // Round-robin + spacing bilan tanlash
        let attempts = 0;
        const maxAttempts = countAsNumber * 10;

        while (selectedQuestions.length < countAsNumber && attempts < maxAttempts) {
            attempts++;

            // Mavzularni shuffle qilib navbatma-navbat olish
            const shuffledLessonIds = [...lessonIds].sort(() => Math.random() - 0.5);

            for (const lessonId of shuffledLessonIds) {
                if (selectedQuestions.length >= countAsNumber) break;

                const availableQuestions = questionsByLesson[lessonId];
                if (!availableQuestions || availableQuestions.length === 0) continue;

                // Spacing tekshirish - oxirgi MIN_SPACING savol ichida shu mavzu bormi
                const recentLessons = selectedQuestions
                    .slice(-MIN_SPACING)
                    .map(q => q.oraliq_dars);

                if (recentLessons.includes(lessonId)) continue;

                // Savolni olish
                const question = availableQuestions.shift();
                if (question) {
                    selectedQuestions.push({ ...question });
                }
            }
        }

        // Agar yetarli savol to'planmasa, qolganlarini qo'shish
        if (selectedQuestions.length < countAsNumber) {
            const selectedIds = new Set(selectedQuestions.map(q => q.id));
            const remaining = oraliqdarslarquestion_db
                .filter(q => lessonIds.includes(q.oraliq_dars) && !selectedIds.has(q.id))
                .sort(() => Math.random() - 0.5);

            while (selectedQuestions.length < countAsNumber && remaining.length > 0) {
                selectedQuestions.push({ ...remaining.shift() });
            }
        }

        // Javoblar va mavzu nomlarini qo'shish
        selectedQuestions.forEach(item => {
            item.answers = oraliqdarslaranswer_db
                .filter(a => a.oraliq_dars_question === item.id)
                .sort(() => Math.random() - 0.5);
            const lesson = oraliqdarslar_db.find(l => l.id === item.oraliq_dars);
            item.lesson_name = {
                "name_ru": oraliq.tartib + '.' + lesson.name_ru,
                "name_uz": oraliq.tartib + '.' + lesson.name_uz,
                "name_cry": oraliq.tartib + '.' + lesson.name_cry
            };
        });

        setOraliqTest(selectedQuestions);
    }, []);

    useEffect(() => {
        fetchOraliqTest(id, count); // Call the memoized function
    }, [id, count, fetchOraliqTest]); // Add fetchOraliqTest to dependencies

    
    if (!OraliqTest || OraliqTest == undefined ||!OraliqTest[0]) return null;



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
                <SolveQuizComponent data={OraliqTest} initialMinutes={count === '50' ? 45 : 25} />
                <Outlet />
            </div>
        </div>
    )
}

export default SolveOraliqTest;
