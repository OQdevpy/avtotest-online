import { Outlet } from "react-router-dom"
import Navbar from "../components/Navbar"
import { useLocation } from 'react-router-dom'
import SolveQuizComponent from "../components/SolveQuizComponent";
import { useCustomContext } from '../context/TestContext';
import SolveQuizComponentWithoutTime from "../components/SolveQuizComponentWithoutTime";


function SolveQuiz() {
    const { Background } = useCustomContext();

    const location = useLocation();
    const { data, time } = location.state || {};
    
    
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
                className="bg-gray-950/90 max-w-full h-full"
                style={{
                    // margin: '1rem', // Removed unnecessary margin
                    // marginBottom: '0.5rem',
                }}
            >
                {
                    time ? <SolveQuizComponent data={ data } /> : <SolveQuizComponentWithoutTime data={ data } />
                }
                <Outlet />
            </div>
        </div>
    )
}

export default SolveQuiz