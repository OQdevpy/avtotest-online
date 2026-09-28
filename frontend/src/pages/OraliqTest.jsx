import { Outlet, useNavigate } from "react-router-dom"
import { useCustomContext } from '../context/TestContext'
import { useEffect, useState } from "react";
import Navbar from "../components/Navbar";


function OraliqTest() {
    const { oraliq, fetchOraliq, Background, getTranslation, getTranslationValue } = useCustomContext();
    const navigate = useNavigate();
    const [showModal, setShowModal] = useState(false);
    const [selectedOraliq, setSelectedOraliq] = useState(null);

    useEffect(() => { fetchOraliq() }, []);

    const handleSectionClick = (section) => {
        setSelectedOraliq(section);
        setShowModal(true);
    };

    const handleSelectCount = (count) => {
        if (selectedOraliq) {
            navigate(`/solve-oraliq/${count}/${selectedOraliq.id}`, {
                state: { oraliq: selectedOraliq, time: true }
            });
        }
        setShowModal(false);
    };

    return (
        <div
            style={{
                backgroundImage: `url(${Background})`,
                backgroundSize: 'cover',
                backgroundRepeat: 'no-repeat',
                backgroundAttachment: 'fixed',
                height: '100vh',
                margin: 0,
                padding: 0,
                overflow: 'hidden'
            }}>
            <Navbar />
            <div style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "80vh",
            }}>
                {/* Section List */}
                <div className="flex flex-col items-center gap-6 md:w-1/2 sm:w-3/4 w-full mx-auto">
                    {oraliq.map((section) => (
                        <button
                            key={section.id}
                            onClick={() => handleSectionClick(section)}
                            className="w-full p-4 text-lg bg-blue-800/30 rounded-lg border border-gray-300 text-white font-semibold transition-transform transform hover:scale-105"
                            style={{ margin: '0 auto', border: '1px solid #ddd' }}
                        >
                            {getTranslationValue(section, "name")}
                        </button>
                    ))}
                </div>

                <Outlet />
            </div>

            {/* Modal */}
            {showModal && (
                <div
                    className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
                    onClick={() => setShowModal(false)}
                >
                    <div
                        className="bg-slate-800 rounded-xl p-6 w-80 max-w-[90vw] border border-slate-600"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h3 className="text-white text-center text-lg font-semibold mb-5">
                            {getTranslation('selectQuestionCount')}
                        </h3>

                        <div className="flex flex-col gap-3">
                            <button
                                onClick={() => handleSelectCount(20)}
                                className="w-full p-4 text-lg bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-all"
                            >
                                20 {getTranslation('questions')}
                            </button>
                            <button
                                onClick={() => handleSelectCount(50)}
                                className="w-full p-4 text-lg bg-green-600 hover:bg-green-700 rounded-lg text-white font-semibold transition-all"
                            >
                                50 {getTranslation('questions')}
                            </button>
                            <button
                                onClick={() => setShowModal(false)}
                                className="w-full p-3 text-sm bg-slate-600 hover:bg-slate-500 rounded-lg text-slate-300 transition-all mt-2"
                            >
                                {getTranslation('cancel')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default OraliqTest