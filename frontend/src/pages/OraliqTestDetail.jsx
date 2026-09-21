import { Outlet } from "react-router-dom";
import { useCustomContext } from '../context/TestContext';
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";

function OraliqTestDetail() {
    const [testCount, setTestCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const { oraliqTest, fetchOraliqTest, Background } = useCustomContext();
    const params = useParams();
    const navigate = useNavigate();


    const handleNavigateOraliq = (count) => {
        navigate(`/solve-test/${count}`);
    };

    const handleBlits = () => {
        navigate(`/blits`);
    }

    const handleBlits2 = () => {
        navigate(`/blits2`);
    }

    const handleBlits3 = () => {
        navigate(`/blits3`);
    }


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
            <div style={
                {
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "80vh",
                }
            }>
                <div className="flex flex-col items-center gap-6 md:w-1/2 sm:w-3/4 w-full mx-auto">


                    <button
                        onClick={() => handleNavigateOraliq(20)}  // Set test count to 20
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            margin: '0 auto',
                            border: '1px solid #ddd',
                        }}
                    >
                        20 
                    </button>
                    <button
                        onClick={() => handleNavigateOraliq(50)}  // Set test count to 50
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            margin: '0 auto',
                            border: '1px solid #ddd',
                        }}
                    >
                        50 
                    </button>
                    <button
                        onClick={() => handleBlits()}  // Set test count to 50
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            margin: '0 auto',
                            border: '1px solid #ddd',
                        }}
                    >
                        Blitz 1
                    </button>
                    <button
                        onClick={() => handleBlits2()}  // Set test count to 50
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            margin: '0 auto',
                            border: '1px solid #ddd',
                        }}
                    >
                        Blitz 2
                    </button>
                    <button
                        onClick={() => handleBlits3()}  // Set test count to 50
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            margin: '0 auto',
                            border: '1px solid #ddd',
                        }}
                    >
                        Blitz 3
                    </button>
                </div>

                <Outlet />
            </div>
        </div>

    );
}

export default OraliqTestDetail;