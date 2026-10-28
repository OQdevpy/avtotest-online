import React, { useState, useEffect } from 'react';
import { MdKeyboardDoubleArrowLeft, MdKeyboardDoubleArrowRight } from "react-icons/md";
import '../assets/styles/style.css';
import DefaultImge from '../assets/default_image.jpg';
import { useNavigate } from 'react-router-dom';
import { useCustomContext } from '../context/TestContext';
import ImageComponent from './ImageComponent';

const OraliqTestDetailComponent = ({ oraliqLessontest }) => {
    const data = oraliqLessontest.oraliqLessontest;
    const navigate = useNavigate();
    const { getTranslation, getTranslationValue } = useCustomContext();

    const handleTestClick = () => {
        const shuffledData = data
            .sort(() => Math.random() - 0.5) // Shuffle the data
            .map(item => ({
                ...item, // Spread the original item
                answers: item.answers.sort(() => Math.random() - 0.5) // Shuffle the answers
            }));
    
        navigate('/solve-quiz', { state: { data: shuffledData } });
    };
    

    const [activeIndex, setActiveIndex] = useState(0);

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (event.key === 'ArrowRight') {
                handleNext();
            } else if (event.key === 'ArrowLeft') {
                handlePrev();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [activeIndex]);

    const handlePrev = () => {
        setActiveIndex((prevIndex) => {
            if (data.length === 0) return prevIndex;

            return prevIndex === 0 ? data.length - 1 : prevIndex - 1;
        });

    };

    const handleNext = () => {
        setActiveIndex((prevIndex) => (prevIndex === data.length - 1 ? 0 : prevIndex + 1));
    };

    const handlePaginationClick = (index) => {
        setActiveIndex(index);
    };

    if (!data || data.length === 0 || !data[activeIndex]) return null;

    const currentItem = data[activeIndex];

    return (
        <div className="container py-5 flex flex-col gap-5">
            <div className="flex flex-col gap-5">
                <div className="flex justify-between gap-2 items-center">

                    <h2 className="text-xl font-bold mx-auto">
                        {getTranslationValue(currentItem, "question")}
                    </h2>
                    <div className="text-blue-400">
                        <button className="btn bg-white rounded-sm border-blue-900 text-blue-900"
                            onClick={handleTestClick}
                        >
                            {getTranslation('solveTest')}

                        </button>
                    </div>
                </div>
                <div className="min-h-20">
                    <div className="flex flex-col md:flex-row justify-between gap-4 my-4">
                        <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full my-6">
                            {currentItem.answers && currentItem.answers.map((answer, index) => (
                                <h2
                                    key={index}
                                    className="btn h-auto p-1 rounded-sm border-blue-900 text-blue-900"
                                    style={{
                                        border: '1px solid #000',
                                        background: answer.is_true ? "#32a852" : 'white',
                                        fontSize: "17px",
                                        width: "100%",
                                    }}
                                >
                                    {getTranslationValue(answer, "answer")}
                                </h2>
                            ))}
                        </div>
                        <ImageComponent currentItem={currentItem} />

                    </div>
                </div>
                <div className="flex items-center gap-2 justify-between py-4">
                    <button className="btn bg-white rounded-sm border-blue-900 text-blue-900" onClick={handlePrev}>
                        <MdKeyboardDoubleArrowLeft size={20} />
                    </button>
                    <div className="flex flex-wrap gap-1 items-center justify-center">
                        {data.map((_, index) => (
                            <div
                                key={index}
                                style={{
                                    background: index === activeIndex ? '#93eded' : 'white',
                                    cursor: "pointer",
                                    width: "2.25rem",
                                    padding: "0.5rem 0",
                                    borderRadius: "0.125rem",
                                    color: "white",
                                    textAlign: "center",
                                    height: "2.5rem",
                                    transition: "all 0.3s",
                                }}
                                onClick={() => handlePaginationClick(index)}
                            >
                                {index + 1}
                            </div>
                        ))}
                    </div>
                    <button className="btn bg-white rounded-sm border-blue-900 text-blue-900" onClick={handleNext}>
                        <MdKeyboardDoubleArrowRight size={20} />
                    </button>
                </div>
            </div>
        </div>

    );
};

export default OraliqTestDetailComponent;
