import { MdLogout } from "react-icons/md";
import { useCustomContext } from "../context/TestContext";
import { useNavigate, useLocation } from "react-router-dom";

function LogOut() {
    const { getTranslation } = useCustomContext();
    const location = useLocation(); // Joriy yo'lni oling
    const navigate = useNavigate(); // Yo'lni o'zgartirish uchun
    const handleReturnPath = () => {
        // Faqat joriy joylashuv bosh sahifasi "/" emasligini tekshiring
        if (location.pathname !== '/') {
            navigate(-1); // O'ng yo'nalishga qaytish
        }
    };

    return (
        <button
            onClick={handleReturnPath}
            className="flex items-center gap-1 text-white uppercase font-semibold"
        >
            <MdLogout size={24} className="rotate-180" /> {/* Ikonani aylantirish */}
            {getTranslation('return')}
        </button>
    );
}

export default LogOut;
