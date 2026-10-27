// Imtihonda birinchi bosilgan (hali tasdiqlanmagan) javob rasm ustida, pastda
// katta qilib ko'rsatiladi (imtihon ilovasidagi kabi). Panel yoki o'sha javob
// qayta bosilsa — javob tekshiriladi.
const SelectedAnswerPanel = ({ index, text, onConfirm }) => (
  <div
    className="absolute bottom-0 left-0 w-full bg-gradient-to-r from-gray-800 to-gray-900 border-2 border-blue-500 shadow-2xl flex items-stretch overflow-hidden cursor-pointer"
    style={{ minHeight: "100px", zIndex: 100 }}
    onClick={onConfirm}
  >
    <span
      className="flex items-center justify-center text-white font-bold"
      style={{ width: "4rem", background: "#3B82F6", fontSize: "24px" }}
    >
      F{index + 1}
    </span>
    <div
      className="flex-1 p-4 text-white flex items-center"
      style={{ fontSize: "20px", lineHeight: "1.5", fontWeight: "500" }}
    >
      {text}
    </div>
  </div>
);

export default SelectedAnswerPanel;
