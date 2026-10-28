import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HiAcademicCap } from "react-icons/hi2";
import { useCustomContext } from '../context/TestContext';

function HomePage() {
    const navigate = useNavigate();
    const { getTranslation } = useCustomContext();

    return (
        <div className="flex justify-center items-center h-screen p-5">
            <div
                className="w-[25vw] h-[32vh] bg-green-500 rounded-lg flex flex-col justify-center items-center p-4 cursor-pointer hover:scale-105 transition-transform"
                onClick={() => navigate('/lessons')}
            >
                <HiAcademicCap className="text-white w-28 h-28 mb-4" />
                <h3 className="text-white text-xl font-semibold">{getTranslation("lessons")}</h3>
            </div>
        </div>
    );
}

export default HomePage;