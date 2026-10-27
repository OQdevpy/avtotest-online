// Imtihonda bosilgan (hali tasdiqlanmagan) javob rasm ustida, vertikal markazda
// javob qatori ko'rinishida chiqadi (imtihon ilovasidagi kabi). Panel
// bosilgandagina javob tekshiriladi; Esc — panelni yopadi.
const SelectedAnswerPanel = ({ index, text, onConfirm }) => (
  <div
    className="absolute left-4 right-4 flex items-stretch border border-gray-500 overflow-hidden shadow-lg cursor-pointer"
    style={{
      minHeight: "60px",
      zIndex: 100,
      top: "50%",
      transform: "translateY(-50%)",
    }}
    onClick={onConfirm}
  >
    <span
      className="flex items-center justify-center text-white font-semibold bg-blue-900/70"
      style={{ width: "3rem", fontSize: "16px" }}
    >
      F{index + 1}
    </span>
    <div
      className="flex-1 p-3 text-white flex items-center bg-blue-950/80 hover:bg-blue-950"
      style={{ border: "1px solid #000", fontSize: "16px", lineHeight: "1.4" }}
    >
      {text}
    </div>
  </div>
);

export default SelectedAnswerPanel;
