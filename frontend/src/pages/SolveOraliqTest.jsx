import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import SolveOraliqQuizComponent from "../components/SolveOraliqQuizComponent";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import oraliq_db from '../db/oraliq.json';
import oraliqdarslar_db from '../db/oraliqdarslar.json';
import oraliqdarslarquestion_db from '../db/oraliqdarslarquestion.json';
import oraliqdarslaranswer_db from '../db/oraliqdarslaranswer.json';

function SolveOraliqTest() {
    const { count, id } = useParams();
    const { oraliqTest,Background } = useCustomContext();
    const [OraliqTest,setOraliqTest] = useState([])
    

    const fetchOraliqTest =  useCallback( async (index, count) => {
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
                <SolveQuizComponent data={OraliqTest} />
                <Outlet />
            </div>
        </div>
    )
}

export default SolveOraliqTest;
