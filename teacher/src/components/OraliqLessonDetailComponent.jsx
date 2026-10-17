import React, { useState, useEffect } from "react";
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from "react-icons/md";
import { FaInfoCircle } from "react-icons/fa";
import "../assets/styles/style.css";

import { useCustomContext } from "../context/TestContext";
import ImageComponent from "./ImageComponent";

const OraliqLessonDetailComponent = ({ oraliqLessontest }) => {
  const data = oraliqLessontest.oraliqLessontest;
  const { getTranslationValue, media_path } = useCustomContext();
  const [showDescImage, setShowDescImage] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [answeredQuestions, setAnsweredQuestions] = useState({}); // Track which questions are answered

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === "ArrowRight") {
        handleNext();
      } else if (event.key === "ArrowLeft") {
        handlePrev();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [activeIndex]);

  const handlePrev = () => {
    setActiveIndex((prevIndex) => {
      if (data.length === 0) return prevIndex;
      return prevIndex === 0 ? data.length - 1 : prevIndex - 1;
    });
  };

  const handleNext = () => {
    setActiveIndex((prevIndex) =>
      prevIndex === data.length - 1 ? 0 : prevIndex + 1
    );
  };

  const handlePaginationClick = (index) => {
    setActiveIndex(index);
  };

  const handleAnswerClick = (answerIndex) => {
    // If question already answered, don't allow more clicks
    if (answeredQuestions[activeIndex] !== undefined) return;

    // Mark this question as answered with the selected answer index
    setAnsweredQuestions((prev) => ({
      ...prev,
      [activeIndex]: answerIndex,
    }));
  };

  const isQuestionAnswered = () => {
    return answeredQuestions[activeIndex] !== undefined;
  };

  const getAnswerColor = (answer, answerIndex) => {
    // If question not answered yet, show default blue
    if (!isQuestionAnswered()) {
      return "#1e40af";
    }

    const selectedIndex = answeredQuestions[activeIndex];

    // If this is the correct answer, always show green
    if (answer.is_true) {
      return "#32a852";
    }

    // If this answer was selected and it's wrong, show red
    if (answerIndex === selectedIndex && !answer.is_true) {
      return "#E53935";
    }

    // Other wrong answers stay blue
    return "#1e40af";
  };

  // Get pagination button color based on answer status
  const getPaginationColor = (index) => {
    // If this is the active question
    if (index === activeIndex) {
      return "#608269"; // Active color (light green)
    }

    // If question was answered
    if (answeredQuestions[index] !== undefined) {
      const selectedAnswerIndex = answeredQuestions[index];
      const questionData = data[index];
      const selectedAnswer = questionData?.answers?.[selectedAnswerIndex];

      if (selectedAnswer?.is_true) {
        return "#32a852"; // Correct - green
      } else {
        return "#E53935"; // Wrong - red
      }
    }

    // Not answered - default gray
    return "#343835";
  };

  if (!data || data.length === 0 || !data[activeIndex]) return null;

  const currentItem = data[activeIndex];

  return (
    <div className="container max-w-full flex flex-col gap-5">
      <div className="flex flex-col gap-0.5">
        <div className="flex justify-between gap-2 items-center">
          <h2 className="text-xl md:text-lg font-bold text-red-100">
            {getTranslationValue(currentItem.lesson_name, "name")}
          </h2>

          {/* Izoh button - always visible if description_image exists */}
          {currentItem.description_image && (
            <button
              className="btn bg-yellow-600/80 text-white flex items-center justify-center border border-yellow-500 cursor-pointer hover:bg-yellow-600"
              onClick={() => setShowDescImage(true)}
              title="Izoh"
              style={{ minWidth: "40px", height: "32px" }}
            >
              <FaInfoCircle size={20} />
            </button>
          )}
        </div>
        <h2
          className="font-bold text-white bg-blue-900/30 flex justify-center items-center"
          style={{ fontSize: "19px" }}
        >
          {getTranslationValue(currentItem, "question")}
        </h2>
      </div>
      <div className="min-h-20">
        <div className="flex flex-col md:flex-row justify-between gap-4">
          <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full">
            {currentItem.answers &&
              currentItem.answers.map((answer, index) => (
                <div
                  key={index}
                  className={`mb-2 flex items-center border border-gray-400 ${isQuestionAnswered() ? 'cursor-default' : 'cursor-pointer hover:opacity-90'}`}
                  onClick={() => handleAnswerClick(index)}
                >
                  <span
                    className="indicator"
                    style={{
                      height: "100%",
                      width: "3rem",
                      backgroundColor: getAnswerColor(answer, index),
                      justifyContent: "center",
                      alignItems: "center",
                      color: "#fff",
                      transition: "background-color 0.3s",
                    }}
                  >
                    F{index + 1}
                  </span>

                  <h2
                    className="p-1 rounded-sm border-blue-900 text-white bg-blue-950/40 min-h-full"
                    style={{
                      border: "1px solid #000",
                      fontSize: "17px",
                      width: "100%",
                    }}
                  >
                    {getTranslationValue(answer, "answer")}
                  </h2>
                </div>
              ))}
          </div>
          <ImageComponent currentItem={currentItem} />
        </div>
      </div>
      <div
        className="flex items-center gap-2 justify-between"
        style={{
          position: "fixed",
          bottom: "0",
          left: "0",
          right: "0",
          zIndex: "1000",
          padding: "10px",
        }}
      >
        <button
          className="btn rounded-sm border-gray-700 text-white bg-gray-500"
          onClick={handlePrev}
        >
          <MdKeyboardDoubleArrowLeft size={20} />
        </button>
        <div className="flex flex-wrap gap-1 items-center justify-center">
          {data.map((_, index) => (
            <div
              key={index}
              style={{
                background: getPaginationColor(index),
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
        <button
          className="btn rounded-sm border-gray-700 text-white bg-gray-500"
          onClick={handleNext}
        >
          <MdKeyboardDoubleArrowRight size={20} />
        </button>
      </div>

      {/* Description Image Modal */}
      {showDescImage && currentItem.description_image && (
        <div
          className="fixed inset-0 z-[2000] flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.85)" }}
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
              src={
                currentItem.description_image.startsWith("data:")
                  ? currentItem.description_image
                  : `${media_path}/${currentItem.description_image}`
              }
              alt="Izoh rasmi"
              className="max-w-full max-h-[85vh] rounded-lg shadow-2xl"
              style={{ objectFit: "contain" }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default OraliqLessonDetailComponent;
