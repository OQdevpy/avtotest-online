import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";
import { fetchBlitsQuestions } from '../api/content';


function BlitsTest() {
    const { id } = useParams();
    const {  Background } = useCustomContext();
    const [solveTest, setSolveTest] = useState([]);
    const [loading, setLoading] = useState(false);   // Loading state
    const [error, setError] = useState(null);        // Error state

        const fetchSolveTest = useCallback(async (blitsId) => {
            try {
                setLoading(true);  // Start loading
                setError(null);    // Reset error state
                setSolveTest(await fetchBlitsQuestions(blitsId));
            } catch (err) {
                setError(err.message || 'Failed to fetch quiz data');
            } finally {
                setLoading(false);  // Stop loading
            }
        }, []);
    
        // Use effect to fetch data when the component mounts
        useEffect(() => {
            fetchSolveTest(id);
        }, [id, fetchSolveTest]);  // Dependency array includes fetchSolveTest
        
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
                    <SolveQuizComponent key={id} data={solveTest} /> 
                }
                <Outlet />
            </div>
        </div>
    )
}

export default BlitsTest;