import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useCustomContext } from '../context/TestContext';

const LessonDetailList = ({ lessons }) => {
    const navigate = useNavigate();
    const { getTranslationValue } = useCustomContext();

    const handleButtonClick = (id) => {
        navigate(`/lesson-detail/${id}`);
    };

    return (
        <div className="flex flex-col items-center justify-center gap-6 w-1/2 mx-auto">
            <div className="flex flex-col gap-6 w-full">
                {lessons.map((lesson, index) => (
                    <button
                        key={lesson.id}
                        onClick={() => handleButtonClick(lesson.id)}
                        className="w-full p-4 text-lg bg-blue-800/30 rounded-lg text-white font-semibold transition-transform transform hover:scale-105"
                        style={{
                            border: '1px solid #ddd',
                            marginTop: index === 0 ? '1rem' : '0',  // Space for the first element
                            marginBottom: index === lessons.length - 1 ? '2rem' : '0',  // Space for the last element
                        }}
                    >
                        {getTranslationValue(lesson, "name")}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default LessonDetailList;
