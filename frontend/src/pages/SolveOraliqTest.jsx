import { Outlet, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { useCustomContext } from '../context/TestContext';
import Navbar from "../components/Navbar";
import SolveQuizComponent from "../components/SolveQuizComponent";
import { fetchSectionTest } from '../api/content';
import { toast } from 'react-toastify';

function SolveOraliqTest() {
    const { count, id } = useParams();
    const { Background } = useCustomContext();
    const [OraliqTest,setOraliqTest] = useState([])
    

    // Bo'lim savollaridan tasodifiy `count` tasi
    const fetchOraliqTest = useCallback(async (index, count) => {
        try {
            setOraliqTest(await fetchSectionTest(index, count));
        } catch (err) {
            toast.error(err.message || 'Failed to fetch quiz data');
        }
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
                <SolveQuizComponent key={`${id}-${count}`} data={OraliqTest} />
                <Outlet />
            </div>
        </div>
    )
}

export default SolveOraliqTest;
