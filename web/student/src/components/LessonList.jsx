import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Navigate } from 'react-router-dom';
import { useCustomContext } from '../context/TestContext';


const   LessonListComponent = ({ oraliq, path }) => {
  if (oraliq.error) {
    return <Navigate to='/login' />;
  }
  const { getTranslationValue } = useCustomContext();

  const navigate = useNavigate();

  const handleButtonClick = (oraliq) => {
    navigate(`${path}/${oraliq.id}`,{ state: { oraliq: oraliq,time:true } });
  };
  
  const handleNavigate = () => {
    navigate(-1);
  }

  return (
    <div className="flex flex-col items-center gap-6 md:w-1/2 sm:w-3/4 w-full mx-auto">
      

      {oraliq.map((lesson) => {
        
        return (
          <button
            key={lesson.id}
            onClick={() => handleButtonClick(lesson)}
            className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
            style={{
              margin: '0 auto',
              border: '1px solid #ddd',
            }}
          >
            {getTranslationValue(lesson,"name")} {/* Display the decoded lesson name */}
          </button>
        );
      })}
    </div>
  );
}

export default LessonListComponent;
