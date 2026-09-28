import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";
import { fetchRandomTest } from '../api/content';
function SolveTest() {
    const { count } = useParams();
    
    const {  Background } = useCustomContext();
    const [solveTest, setSolveTest] = useState([]);
    const [loading, setLoading] = useState(false);   // Loading state
    const [error, setError] = useState(null);        // Error state

        const fetchSolveTest = useCallback(async (count) => {
            try {
                setLoading(true);  // Start loading
                setError(null);    // Reset error state
                // Server barcha savollardan tasodifiy 20 yoki 50 tasini tanlaydi
                setSolveTest(await fetchRandomTest(Number(count)));
            } catch (err) {
                setError(err.message || 'Failed to fetch quiz data');
            } finally {
                setLoading(false);  // Stop loading
            }
        }, []);
    
        // Use effect to fetch data when the component mounts
        useEffect(() => {
            fetchSolveTest(count);
        }, [count, fetchSolveTest]);  // Dependency array includes fetchSolveTest
        
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
                    time ? <SolveQuizComponent key={count} data={solveTest} /> : <SolveQuizComponentWithoutTime key={count} data={solveTest} />
                }
                <Outlet />
            </div>
        </div>
    )
}

export default SolveTest;
