import { Outlet } from "react-router-dom";
import { useCustomContext } from '../context/TestContext';
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Navbar from "../components/Navbar";
import { blits_db } from '../utils/dataLoader';

function OraliqTestDetail() {
    const [testCount, setTestCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const { oraliqTest, fetchOraliqTest, Background } = useCustomContext();
    const params = useParams();
    const navigate = useNavigate();


    const handleNavigateOraliq = (count) => {
        navigate(`/solve-test/${count}`);
    };

    const handleBlits = (blitsId) => {
        navigate(`/blits/${blitsId}`);
    };


    return (
        <div
            style={{
                backgroundImage: `url(${Background})`,
                backgroundSize: 'cover',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed',
                height: '100vh',
                margin: 0,
                padding: 0,
                overflow: 'hidden'
            }}>
            <Navbar />
            <div style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "80vh",
            }}>
                <div className="flex flex-col items-center gap-6 md:w-1/2 sm:w-3/4 w-full mx-auto">

                    <button
                        onClick={() => handleNavigateOraliq(20)}
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{ margin: '0 auto', border: '1px solid #ddd' }}
                    >
                        20 
                    </button>
                    <button
                        onClick={() => handleNavigateOraliq(50)}
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                        style={{ margin: '0 auto', border: '1px solid #ddd' }}
                    >
                        50 
                    </button>

                    {blits_db.map((blits) => (
                        <button
                            key={blits.id}
                            onClick={() => handleBlits(blits.id)}
                            className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                            style={{ margin: '0 auto', border: '1px solid #ddd' }}
                        >
                            {blits.name_uz}
                        </button>
                    ))}
                </div>

                <Outlet />
            </div>
        </div>
    );
}

export default OraliqTestDetail;