import React, { useState, useEffect, useRef } from 'react';
import { MdKeyboardDoubleArrowLeft, MdKeyboardDoubleArrowRight } from "react-icons/md";
import { FaInfoCircle } from "react-icons/fa";
import DefaultImge from '../assets/default_image.jpg';
import { useNavigate } from 'react-router-dom';
import { useCustomContext } from '../context/TestContext';
import Time from './Time';
import ImageComponent from './ImageComponent';

const SolveOraliqQuizComponent = ({ data }) => {
    const navigate = useNavigate();
    const timeRef = useRef(null);
    const [variant, setVariant] = useState(data.data);

    if (!Array.isArray(variant) || variant.length === 0) {
        return <p>No data available</p>;
    }

    if (variant.error) {
        return navigate('/login');
    }

    const [activeIndex, setActiveIndex] = useState(0);
    const [answered, setAnswered] = useState({});
    const [timeEnded, setTimeEnded] = useState(false);
    const [trueCount, setTrueCount] = useState(0);
    const [showDescImage, setShowDescImage] = useState(false);
    const { getTranslation, getTranslationValue, media_path, returnResult } = useCustomContext();

    const handlePrev = () => {
        setActiveIndex((prevIndex) => (prevIndex === 0 ? variant.length - 1 : prevIndex - 1));
    };

    const handleNext = () => {
        setActiveIndex((prevIndex) => (prevIndex === variant.length - 1 ? 0 : prevIndex + 1));
    };

    const handlePaginationClick = (index) => {
        setActiveIndex(index);
    };

    const handleTimeEnd = () => {
        setTimeEnded(true);
    };

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

    // Close description modal when changing questions
    useEffect(() => {
        setShowDescImage(false);
    }, [activeIndex]);

    const checkAnswers = (item, index, activeIndex) => {
        setAnswered((prevAnswered) => ({ ...prevAnswered, [activeIndex]: index }));
        if (item.is_true) {
            setTrueCount((prevTrueCount) => prevTrueCount + 1);
        }
    };

    const isAnswered = (index) => {
        return answered[index] !== undefined;
    };

    const checkButton = (index) => {
        if (activeIndex === index) {
            return '#93eded';
        }
        if (answered[index] !== undefined) {
            return variant[index].answers[answered[index]].is_true ? '#43A047' : '#E53935';
        }
        return timeEnded ? '#E53935' : 'white';
    };

    const reset = () => {
        setAnswered({});
        setActiveIndex(0);
        setTimeEnded(false);
        setTrueCount(0);
        setShowDescImage(false);
        if (timeRef.current) {
            timeRef.current.resetTime();  // Call the resetTime method
        };
        setVariant(data.data.sort(() => Math.random() - 0.5));
    };

    const color = (index, activeIndex) => {
        if (timeEnded || answered[activeIndex] !== undefined) {
            if (index === answered[activeIndex]) {
                return variant[activeIndex].answers[index].is_true ? '#43A047' : '#E53935';
            }
            return variant[activeIndex].answers[index].is_true ? '#43A047' : 'transparent';
        }
        return 'transparent';
    };

    const handleTestClick = () => {
        if (timeEnded || variant.length === Object.keys(answered).length) navigate(0);
        else navigate(-1);
    };

    if (variant === null) return null;

    return (
        <div className="container py-5 flex flex-col gap-5">
            <div className='flex items-center gap-1 justify-center'>
                {
                    variant.length === Object.keys(answered).length ? <div className='text-xl font-bold text-center text-blue-600'>{returnResult(trueCount, variant.length)}</div> :
                        <div className='flex gap-2'>
                            <Time onTimeEnd={handleTimeEnd} ref={timeRef} />  {/* Pass the ref to Time component */}
                            {timeEnded && (
                                <div className='text-xl font-bold text-center text-blue-600'>{returnResult(trueCount, variant.length)}</div>
                            )}
                        </div>
                }
            </div>
            <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2 justify-between">

                    <h2 className="text-xl font-bold">
                        {getTranslationValue(variant[activeIndex], "question")}
                    </h2>
                    <div className="flex items-center gap-2">
                        {/* Izoh button - only show when answered and has description_image */}
                        {isAnswered(activeIndex) && variant[activeIndex].description_image && (
                            <button
                                className="btn bg-yellow-600/80 text-white flex items-center justify-center border border-yellow-500 cursor-pointer hover:bg-yellow-600"
                                onClick={() => setShowDescImage(true)}
                                title="Izoh"
                                style={{ minWidth: '40px', height: '40px' }}
                            >
                                <FaInfoCircle size={20} />
                            </button>
                        )}
                        <button
                            className="btn bg-white rounded-sm border-blue-900 text-blue-900"
                            onClick={() => reset()}
                        >
                            {getTranslation('startZero')}
                        </button>
                    </div>
                </div>

                <div className="min-h-20">
                    <div className="flex flex-col md:flex-row justify-between gap-4 my-4">
                        <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full my-6">
                            {variant[activeIndex].answers.map((answer, index) => (
                                <button
                                    disabled={isAnswered(activeIndex) || timeEnded}
                                    onClick={() => checkAnswers(answer, index, activeIndex)}
                                    key={index}
                                    className={`btn h-auto p-1 rounded-sm border-blue-900 text-blue-900`}
                                    style={{
                                        background: color(index, activeIndex),
                                        border: '1px solid #000',
                                        color: isAnswered(activeIndex) || timeEnded ? '#000' : '#1e3a8a',
                                        fontSize: "17px",
                                        width: "100%",
                                    }}
                                >
                                    {getTranslationValue(answer, "answer")}
                                </button>
                            ))}
                        </div>
                        <ImageComponent currentItem={variant[activeIndex]} />

                    </div>
                </div>

                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        padding: "8px 0"
                    }}
                >
                    <button className="btn rounded-sm border-gray-700 text-white bg-gray-500" onClick={handlePrev}>
                        <MdKeyboardDoubleArrowLeft size={20} />
                    </button>
{variant.length === 50 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", alignItems: "center" }}>
                            <div style={{ display: "flex", gap: "0.25rem" }}>
                                {variant.slice(0, 25).map((_, index) => (
                                    <div
                                        key={index}
                                        style={{
                                            background: checkButton(index),
                                            cursor: 'pointer',
                                            width: '2.25rem',
                                            padding: '0.5rem 0',
                                            borderRadius: '0.125rem',
                                            color: 'white',
                                            textAlign: 'center',
                                            height: '2.5rem',
                                            transition: 'all 0.3s',
                                        }}
                                        onClick={() => handlePaginationClick(index)}
                                    >
                                        {index + 1}
                                    </div>
                                ))}
                            </div>
                            <div style={{ display: "flex", gap: "0.25rem" }}>
                                {variant.slice(25, 50).map((_, index) => (
                                    <div
                                        key={index + 25}
                                        style={{
                                            background: checkButton(index + 25),
                                            cursor: 'pointer',
                                            width: '2.25rem',
                                            padding: '0.5rem 0',
                                            borderRadius: '0.125rem',
                                            color: 'white',
                                            textAlign: 'center',
                                            height: '2.5rem',
                                            transition: 'all 0.3s',
                                        }}
                                        onClick={() => handlePaginationClick(index + 25)}
                                    >
                                        {index + 26}
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", justifyContent: "center" }}>
                            {variant.map((_, index) => (
                                <div
                                    key={index}
                                    style={{
                                        background: checkButton(index),
                                        cursor: 'pointer',
                                        width: '2.25rem',
                                        padding: '0.5rem 0',
                                        borderRadius: '0.125rem',
                                        color: 'white',
                                        textAlign: 'center',
                                        height: '2.5rem',
                                        transition: 'all 0.3s',
                                    }}
                                    onClick={() => handlePaginationClick(index)}
                                >
                                    {index + 1}
                                </div>
                            ))}
                        </div>
                    )}
                    <button className="btn rounded-sm border-gray-700 text-white bg-gray-500" onClick={handleNext}>
                        <MdKeyboardDoubleArrowRight size={20} />
                    </button>
                </div>
            </div>

            {/* Description Image Modal */}
            {showDescImage && variant[activeIndex].description_image && (
                <div
                    className="fixed inset-0 z-[2000] flex items-center justify-center"
                    style={{ background: 'rgba(0,0,0,0.85)' }}
                    onClick={() => setShowDescImage(false)}
                >
                    <div
                        className="relative max-w-4xl max-h-[90vh] p-2"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button
                            onClick={() => setShowDescImage(false)}
                            className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-lg cursor-pointer hover:bg-red-700 z-10"
                        >
                            ×
                        </button>
                        <img
                            src={variant[activeIndex].description_image.startsWith('data:')
                                ? variant[activeIndex].description_image
                                : `${media_path}/${variant[activeIndex].description_image}`}
                            alt="Izoh rasmi"
                            className="max-w-full max-h-[85vh] rounded-lg shadow-2xl"
                            style={{ objectFit: 'contain' }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

export default SolveOraliqQuizComponent;
