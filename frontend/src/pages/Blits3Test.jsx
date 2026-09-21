import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";
import oraliq_db from '../db/oraliq.json';
import answer_db from '../db/answer.json';
import image_db from '../db/image.json';
import oraliqdarslaranswer_db from '../db/oraliqdarslaranswer.json';
import oraliqdarslar_db from '../db/oraliqdarslar.json';
import oraliqdarslarquestion_db from '../db/oraliqdarslarquestion.json';
import blitsQuestion_db from '../db/blitsquestion3.json';


function Blits3Test() {
    const {  Background } = useCustomContext();
    const [solveTest, setSolveTest] = useState([]);
    const [loading, setLoading] = useState(false);   // Loading state
    const [error, setError] = useState(null);        // Error state

        const fetchSolveTest = useCallback(async () => {
            try {
                setLoading(true);  // Start loading
                setError(null);    // Reset error state
    
                // Shuffle questions and select based on count
                function shuffleArray(array) {
                    for (let i = array.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [array[i], array[j]] = [array[j], array[i]];
                    }
                    return array;
                }
                
                const randomQuestions = shuffleArray(blitsQuestion_db);
    
                // Add answers and lesson names
                randomQuestions.forEach(item => {
                    item.answers = oraliqdarslaranswer_db.filter((new_item) => new_item.oraliq_dars_question === item.id).sort(() => Math.random() - 0.5);
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
    
        // Use effect to fetch data when the component mounts
        useEffect(() => {
            fetchSolveTest();
        }, [fetchSolveTest]);  // Dependency array includes fetchSolveTest
        
        // Conditional rendering based on loading or error states
        
        if (loading) return <p>Loading...</p>;
        if (error) return <p>{error}</p>;
        if (!solveTest || solveTest.length === 0) return <p>No data available</p>;
    







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
                    <SolveQuizComponent data={solveTest} /> 
                }
                <Outlet />
            </div>
        </div>
    )
}

export default Blits3Test;