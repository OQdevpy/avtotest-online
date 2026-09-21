import { Outlet, useLocation } from "react-router-dom";

import Navbar from "../components/Navbar";
import LessonDetailList from "../components/LessonDetailList";
import { useCustomContext } from '../context/TestContext';
import { useEffect } from "react";
import { useParams } from "react-router-dom";

function LessonDetail() {
    const params = useParams();
    const { lessons, fetchLessons, getTranslationValue, Background } = useCustomContext();
    useEffect(() => { fetchLessons(params.id) }, [params.id]);
    const location = useLocation();
    const { oraliq } = location.state || {};

    return (
        <div style={{
            backgroundImage: `url(${Background})`,
            backgroundSize: 'cover',
            backgroundRepeat: 'no-repeat',
            height: '100vh',
            margin: 0,
            padding: 0,
            overflow: 'hidden'
        }}>
            <Navbar />
            <h2 className="text-xl fixed font-bold text-red-200 ml-6 mt-6 z-10">
                {getTranslationValue(oraliq, "name")}
            </h2>
            <div style={{
                display: "flex",
                flexDirection: "column",
                height: "calc(100vh - 6rem)",  // Adjust based on the height of your fixed header
                paddingTop: '6rem', // Adjust based on the height of your fixed header
                paddingBottom: '1rem', // Ensure there's space at the bottom
                overflowY: 'auto',
            }}>
                <LessonDetailList lessons={lessons} />
                <Outlet />
            </div>
        </div>
    );
}

export default LessonDetail;
