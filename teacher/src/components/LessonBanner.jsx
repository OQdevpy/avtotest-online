import { useEffect } from "react";
import { useCustomContext } from "../context/TestContext";

// Dars ochilganda savollardan oldin katta ko'rsatiladigan banner (o'qituvchi uni
// o'quvchilarga ko'rsatib tushuntiradi). Enter, →, Probel yoki tugma — savollarga.
const LessonBanner = ({ src, title, onContinue }) => {
  const { getTranslation } = useCustomContext();

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (["Enter", "ArrowRight", " ", "Escape"].includes(event.key)) {
        event.preventDefault();
        onContinue();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onContinue]);

  return (
    <div className="fixed inset-x-0 bottom-0 top-16 z-[1500] flex flex-col items-center justify-center gap-5 bg-gray-950 p-4">
      {title && <h2 className="text-xl font-bold text-red-100 text-center">{title}</h2>}
      <img
        src={src}
        alt={title || "Banner"}
        className="max-w-full max-h-[72vh] rounded-lg shadow-2xl"
        style={{ objectFit: "contain" }}
      />
      <button
        onClick={onContinue}
        className="px-8 py-3 rounded-md bg-blue-800 text-white text-lg font-semibold uppercase hover:bg-blue-700"
      >
        {getTranslation("toQuestions")} →
      </button>
    </div>
  );
};

export default LessonBanner;
