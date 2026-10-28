import React from 'react';
import { useNavigate } from 'react-router-dom';
import { HiAcademicCap } from "react-icons/hi2";
import { TfiCheckBox } from "react-icons/tfi";
import { MdQuiz, MdOutlineQuiz } from "react-icons/md";
import { FaUserCheck } from "react-icons/fa";

import { useCustomContext } from '../context/TestContext';
function HomePage() {
    const navigate = useNavigate();

    const handleCardClick = (path) => {
        navigate(path);
    };

    const { getTranslation } = useCustomContext();

      const getUserDeviceInfo = () => {
        const userAgentData = navigator.userAgentData || {};
        console.log("User Agent Data:", userAgentData);
      };
      
      getUserDeviceInfo();
      
      const getUserDeviceIfo = () => {
        const userAgent = navigator.userAgent;
        console.log("User Agent:", userAgent);
      };
      
      getUserDeviceIfo();
      
    return (
        <div className="flex justify-center items-center h-screen p-5 ">
            <div className="flex justify-center items-center h-screen p-5">
                <div className="flex flex-col md:flex-row justify-center items-center space-y-5 md:space-y-0 md:space-x-10">
                    <div
                        className="w-[21vw] h-[28vh]   bg-green-500 rounded-lg flex flex-col justify-center items-center p-4 cursor-pointer"
                        onClick={() => handleCardClick('/lessons')}
                    >
                        <HiAcademicCap className="text-white w-24 h-24 mb-4" />
                        <h3 className="text-white text-lg font-semibold">{getTranslation("lessons")}</h3>
                    </div>
                    <div
                        className="w-[21vw] h-[28vh]   bg-yellow-500 rounded-lg flex flex-col justify-center items-center p-4 cursor-pointer"
                        onClick={() => handleCardClick('/oraliq-test')}
                    >
                        <TfiCheckBox className="text-white w-24 h-24 mb-4" />
                        <h3 className="text-white text-lg font-semibold">{getTranslation("oraliqTest")}</h3>
                    </div>
                    <div
                        className="w-[21vw] h-[28vh]   bg-red-500 rounded-lg flex flex-col justify-center items-center p-4 cursor-pointer"
                        onClick={() => handleCardClick('/solve-test')}
                    >
                        <FaUserCheck className="text-white w-24 h-24 mb-4" />
                        <h3 className="text-white text-lg font-semibold">{getTranslation("exam")}</h3>
                    </div>
                    <div
                        className="w-[21vw] h-[28vh]   bg-gray-500 rounded-lg flex flex-col justify-center items-center p-4 cursor-pointer"
                        onClick={() => handleCardClick('/variants')}
                    >
                        <MdOutlineQuiz className="text-white w-24 h-24 mb-4" />
                        <h3 className="text-white text-lg font-semibold">{getTranslation("variants")}</h3>
                    </div>
                </div>
            </div>

        </div>
    );
}

export default HomePage;