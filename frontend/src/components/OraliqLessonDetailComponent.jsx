import React, { useState, useEffect } from "react";
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from "react-icons/md";
import "../assets/styles/style.css";

import { useNavigate } from "react-router-dom";
import { useCustomContext } from "../context/TestContext";
import ImageComponent from "./ImageComponent";

const OraliqLessonDetailComponent = ({ oraliqLessontest }) => {
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

    navigate('/solve-quiz', { state: { data: shuffledData },time: false  });
};

  const [activeIndex, setActiveIndex] = useState(0);

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

  if (!data || data.length === 0 || !data[activeIndex]) return null;

  const currentItem = data[activeIndex];
  
  return (
    <div className="container max-w-full  flex flex-col gap-5 ">
      <div className="flex flex-col gap-0.5">
        <div className="flex justify-between gap-2 items-center">
          <h2 className="text-xl md:text-lg font-bold text-red-100 ">
            {getTranslationValue(currentItem.lesson_name, "name")}
          </h2>

          <div className="text-blue-500 flex-shrink-0 justify-center items-center min-w-[220px]">
            {" "}
            {/* Adjusted for consistent width */}
            <button
              className="btn bg-blue-950/60 text-white flex items-center border border-blue-900 p-2 cursor-pointer  w-full hover:bg-blue-950/60"
              onClick={() => handleTestClick()}
              style={{ width: "100%" }} // Ensure button fills the available space
            >
              {getTranslation("solveTest")}
            </button>
          </div>
        </div>
        <h2 className=" font-bold text-white  bg-blue-900/30 flex justify-center items-center" style={{ fontSize: '19px', }}>
          {getTranslationValue(currentItem, "question")}
        </h2>
      </div>
      <div className="min-h-20">
        <div className="flex flex-col md:flex-row justify-between gap-4">
          <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full ">
            {currentItem.answers &&
              currentItem.answers.map((answer, index) => (
                <div
                  key={index}
                  className="mb-2 flex items-center border border-gray-400"
                  style={{}}
                >
                  <span
                    className="indicator"
                    style={{
                      height: "100%",
                      width: "3rem",
                      backgroundColor: answer.is_true ? "#32a852" : "blue",
                      justifyContent: "center",
                      alignItems: "center",
                      color: "#fff",
                    }}
                  >
                    F{index + 1}
                  </span>

                  <h2
                    className=" p-1 rounded-sm border-blue-900 text-white bg-blue-950/40 min-h-full"
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
          position: "fixed", // Fixed positioning to make it static
          bottom: "0", // Stick to the bottom of the page
          left: "0", // Align with the left edge
          right: "0", // Stretch to the right edge
          zIndex: "1000", // Make sure it's on top of other elements
          padding: "10px", // Add some padding for visual comfort
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
                background: index === activeIndex ? "#608269" : "#343835",
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
    </div>
  );
};

export default OraliqLessonDetailComponent;
