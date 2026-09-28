import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";
import {
  oraliq_db, oraliqdarslar_db, oraliqdarslaranswer_db,
  blits_questions_db,
} from '../utils/dataLoader';


function BlitsTest() {
    const { blitsId } = useParams();
    const { Background } = useCustomContext();
    const [solveTest, setSolveTest] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchSolveTest = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const blitsQuestions = blits_questions_db[blitsId];
            if (!blitsQuestions || blitsQuestions.length === 0) {
                setError('No questions found for this blits');
                return;
            }

            function shuffleArray(array) {
                const arr = [...array];
                for (let i = arr.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [arr[i], arr[j]] = [arr[j], arr[i]];
                }
                return arr;
            }

            const randomQuestions = shuffleArray(blitsQuestions).map(q => ({ ...q }));

            randomQuestions.forEach(item => {
                item.answers = oraliqdarslaranswer_db
                    .filter((a) => a.oraliq_dars_question === item.id)
                    .sort(() => Math.random() - 0.5);
                const lesson = oraliqdarslar_db.find((l) => l.id === item.oraliq_dars);
                const oraliq = oraliq_db.find((o) => o.id === lesson.oraliq);
                item.lesson_name = {
                    name_ru: `${oraliq.tartib}.${lesson.name_ru}`,
                    name_uz: `${oraliq.tartib}.${lesson.name_uz}`,
                    name_cry: `${oraliq.tartib}.${lesson.name_cry}`,
                };
            });

            setSolveTest([...randomQuestions]);
        } catch (err) {
            setError('Failed to fetch quiz data');
        } finally {
            setLoading(false);
        }
    }, [blitsId]);

    useEffect(() => {
        fetchSolveTest();
    }, [fetchSolveTest]);

    if (loading) return <p>Loading...</p>;
    if (error) return <p>{error}</p>;
    if (!solveTest || solveTest.length === 0) return <p>No data available</p>;

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
            >
                <SolveQuizComponentWithoutTime data={solveTest} />
                <Outlet />
            </div>
        </div>
    );
}

export default BlitsTest;