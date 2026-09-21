import React, { useState, useEffect, useRef } from "react";
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from "react-icons/md";
import { useNavigate } from "react-router-dom";
import { useCustomContext } from "../context/TestContext";
import ImageComponent from "./ImageComponent";

const SolveQuizComponentWithoutTime = ({ data }) => {

  const navigate = useNavigate();
  const [variant, setVariant] = useState(data);

  if (!Array.isArray(variant) || variant.length === 0 || variant == null) {
    return <p>No data available</p>;
  }

  // useEffect(() => {
  //   setVariant(data)
  // }, [])

  // if (variant.error) {
  //   return navigate("/login");
  // }

  const [activeIndex, setActiveIndex] = useState(0);
  const [answered, setAnswered] = useState({});
  const [trueCount, setTrueCount] = useState(0);

  const { getTranslation, getTranslationValue, returnResult } = useCustomContext();



  const handlePrev = () => {
    setActiveIndex((prevIndex) => {

      return prevIndex === 0 ? variant.length - 1 : prevIndex - 1;

    });
  };

  const handleNext = () => {
    setActiveIndex((prevIndex) => {

      return prevIndex === variant.length - 1 ? 0 : prevIndex + 1;
    });
  };

  const handlePaginationClick = (index) => {
    
    setActiveIndex(index);

  };

  const checkAnswers = (item, index, activeIndex) => {
    setAnswered((prevAnswered) => ({ ...prevAnswered, [activeIndex]: index }));
    if (item.is_true) {
      setTrueCount((prevTrueCount) => prevTrueCount + 1);
  }
    setTimeout(() => {
      handleNext();
    }, 2000);

  };

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


  const isAnswered = (index) => {
    return answered[index] !== undefined;
  };

  const checkButton = (index) => {
    if (activeIndex === index) {
      return "#608269";
    }
    if (answered[index] !== undefined) {
      return variant[index].answers[answered[index]].is_true
        ? "#43A047"
        : "#E53935";
    }
    return "#343835";
  };

  const color = (index, activeIndex) => {
    if (answered[activeIndex] !== undefined) {
      if (index === answered[activeIndex]) {
        return variant[activeIndex].answers[index].is_true
          ? "#43A047"
          : "#E53935";
      }
      return variant[activeIndex].answers[index].is_true
        ? "#43A047"
        : "transparent";
    }
    return "transparent";
  };

  const reset = () => {
    setAnswered({});
    setActiveIndex(0);
    setVariant(data.sort(() => Math.random() - 0.5));
    setTrueCount(0);
    
  };


  if (variant === null) return null;

  return (
    <div className="container max-w-full flex flex-col gap-5">
      <div className="flex flex-col gap-0.5">
        <div className="flex justify-between gap-2 items-center">
          <h2 className="text-xl font-bold text-red-100">
            {getTranslationValue(variant[activeIndex].lesson_name, "name")}
          </h2>

          <div className="flex items-center gap-2 flex-grow justify-center text-white">
            {variant.length === Object.keys(answered).length ? (
              returnResult(trueCount, variant.length)
            ) : null}
          </div>

          <div className="text-blue-500 flex-shrink-0" style={{ minWidth: "160px" }}>
            <button
              className="btn bg-blue-950/60 text-white flex items-center border border-blue-900 p-2 cursor-pointer h-10 w-full hover:bg-blue-950/60"
              onClick={() => reset()}
              style={{ width: "100%" }}
            >
              {getTranslation("startZero")}
            </button>
          </div>
        </div>
      </div>

      <h2
        className="font-bold text-white bg-blue-900/30 flex justify-center items-center p-1 w-full"
        style={{ fontSize: "20px" }}
      >
        {getTranslationValue(variant[activeIndex], "question")}
      </h2>

      <div className="min-h-20 ">
        <div className="flex flex-col md:flex-row justify-between gap-4">
          <div className="flex flex-col gap-2 md:w-1/3 sm:w-1/2 w-full flex-grow">
            {variant[activeIndex].answers.map((answer, index) => (
              <div key={index} className="mb-2 flex items-center border border-gray-500">
                <span
                  className="indicator"
                  style={{
                    height: "100%",
                    width: "3rem",
                    background: color(index, activeIndex),
                    color: "#fff",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  F{index + 1}
                </span>
                <h2
                  className="p-1 rounded-sm border-blue-900 text-white bg-blue-950/40 min-h-full hover:bg-blue-950"
                  style={{
                    border: "1px solid #000",
                    fontSize: "17px",
                    width: "100%",
                    cursor: isAnswered(activeIndex) ? "not-allowed" : "pointer",
                  }}
                  onClick={() => {
                    if (!isAnswered(activeIndex)) {
                      checkAnswers(answer, index, activeIndex);
                    }
                  }}
                >
                  {getTranslationValue(answer, "answer")}
                </h2>
              </div>
            ))}
          </div>
          <ImageComponent currentItem={variant[activeIndex]} />
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
          className="btn  rounded-sm border-gray-700 text-white bg-gray-500 "
          onClick={handlePrev}
        >
          <MdKeyboardDoubleArrowLeft size={16} />
        </button>
        <div className="flex flex-wrap gap-1 items-center justify-center">
          {variant.map((_, index) => (
            <div
              key={index}
              style={{
                background: checkButton(index),
                width: "2.25rem",
                padding: "0.5rem 0",
                borderRadius: "0.125rem",
                // border: '1px solid #1e3a8a',
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
          className="btn  rounded-sm border-gray-700 text-white bg-gray-500"
          onClick={handleNext}
        >
          <MdKeyboardDoubleArrowRight size={16} />
        </button>
      </div>
    </div>
  );
};

export default SolveQuizComponentWithoutTime;
