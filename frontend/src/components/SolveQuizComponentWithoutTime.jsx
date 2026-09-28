import React, { useState, useEffect, useRef } from "react";
import {
  MdKeyboardDoubleArrowLeft,
  MdKeyboardDoubleArrowRight,
} from "react-icons/md";
import { FaInfoCircle } from "react-icons/fa";
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
  const [showDescImage, setShowDescImage] = useState(false);

  const { getTranslation, getTranslationValue, returnResult, media_path } = useCustomContext();



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

  // Close description modal when changing questions
  useEffect(() => {
    setShowDescImage(false);
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
    setShowDescImage(false);
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

          <div className="text-blue-500 flex-shrink-0 flex items-center gap-2" style={{ minWidth: "200px" }}>
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
              className="btn bg-blue-950/60 text-white flex items-center border border-blue-900 p-2 cursor-pointer h-10 flex-1 hover:bg-blue-950/60"
              onClick={() => reset()}
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
        style={{
          position: "fixed",
          bottom: "0",
          left: "0",
          right: "0",
          zIndex: "1000",
          padding: "10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px"
        }}
      >
        <button
          className="btn rounded-sm border-gray-700 text-white bg-gray-500"
          onClick={handlePrev}
        >
          <MdKeyboardDoubleArrowLeft size={16} />
        </button>
        {variant.length === 50 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", alignItems: "center" }}>
            <div style={{ display: "flex", gap: "0.25rem" }}>
              {variant.slice(0, 25).map((_, index) => (
                <div
                  key={index}
                  style={{
                    background: checkButton(index),
                    width: "2.25rem",
                    padding: "0.5rem 0",
                    borderRadius: "0.125rem",
                    color: "white",
                    textAlign: "center",
                    height: "2.5rem",
                    transition: "all 0.3s",
                    cursor: "pointer"
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
                    width: "2.25rem",
                    padding: "0.5rem 0",
                    borderRadius: "0.125rem",
                    color: "white",
                    textAlign: "center",
                    height: "2.5rem",
                    transition: "all 0.3s",
                    cursor: "pointer"
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
                  width: "2.25rem",
                  padding: "0.5rem 0",
                  borderRadius: "0.125rem",
                  color: "white",
                  textAlign: "center",
                  height: "2.5rem",
                  transition: "all 0.3s",
                  cursor: "pointer"
                }}
                onClick={() => handlePaginationClick(index)}
              >
                {index + 1}
              </div>
            ))}
          </div>
        )}
        <button
          className="btn rounded-sm border-gray-700 text-white bg-gray-500"
          onClick={handleNext}
        >
          <MdKeyboardDoubleArrowRight size={16} />
        </button>
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

export default SolveQuizComponentWithoutTime;
