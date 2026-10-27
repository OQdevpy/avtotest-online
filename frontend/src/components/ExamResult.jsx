import { useNavigate } from "react-router-dom";
import { useCustomContext } from "../context/TestContext";

// Imtihon (20/50) tugaganda savollar o'rniga ekran o'rtasida katta natija
// chiqadi (imtihon ilovasidagi natija sahifasi kabi).
const ExamResult = ({ trueCount, questionCount, onRestart }) => {
  const navigate = useNavigate();
  const { getTranslation } = useCustomContext();

  const percentage = (trueCount / questionCount) * 100;
  // returnResult bilan bir xil chegara: 50 ta — 92%, boshqa — 90%
  const passed = percentage >= (questionCount === 50 ? 92 : 90);
  const colorClass = passed ? "text-green-500" : "text-red-500";

  return (
    <div
      className="fixed inset-0 flex flex-col items-center justify-center text-center text-white px-4 bg-gray-950/95"
      style={{ zIndex: 1500 }}
    >
      <h1
        className={`font-bold mb-12 drop-shadow-2xl leading-tight ${colorClass}`}
        style={{ fontSize: "clamp(2.5rem, 6vw, 6rem)" }}
      >
        {getTranslation(passed ? "examPassedText" : "examFailedText")}
      </h1>
      <div className="text-4xl font-bold mb-12">
        {`${getTranslation("totalScore")}: ${trueCount} / ${questionCount} (${percentage.toFixed(2)}%)`}
      </div>
      <div className="flex gap-4">
        <button
          onClick={onRestart}
          className="px-8 py-5 text-xl bg-blue-950/60 border border-blue-900 rounded-lg text-white hover:bg-blue-950 transition duration-300"
          style={{ minWidth: 200 }}
        >
          {getTranslation("startZero")}
        </button>
        <button
          onClick={() => navigate("/")}
          className="px-8 py-5 text-xl bg-blue-500 rounded-lg text-white hover:bg-blue-600 transition duration-300"
          style={{ minWidth: 200 }}
        >
          {getTranslation("menu")}
        </button>
      </div>
    </div>
  );
};

export default ExamResult;
