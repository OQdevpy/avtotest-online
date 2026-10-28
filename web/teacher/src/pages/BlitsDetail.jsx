import React from 'react'
import Navbar from '../components/Navbar'
import OraliqLessonDetailComponent from '../components/OraliqLessonDetailComponent'
import { Outlet } from 'react-router-dom'
import { useCustomContext } from '../context/TestContext'
import { useEffect } from "react";
import { useParams } from "react-router-dom";


function BlitsDetail() {
    const { blitsTest, fetchBlitsTest, Background } = useCustomContext();
    const params = useParams();

    useEffect(() => {
        fetchBlitsTest(params.id);
    }, [params.id]);

    return (
        <div style={{
            backgroundImage: `url(${Background})`,
            backgroundSize: 'cover',
            backgroundRepeat: 'no-repeat',
            overflow: 'hidden',
            height: '100vh',
        }}>
            <Navbar />
            <div
                className="bg-gray-950/90 max-w-full w-full  h-full "
            >
                <OraliqLessonDetailComponent oraliqLessontest={{ oraliqLessontest: blitsTest }} />
                <Outlet />
            </div>
        </div>
    )
}

export default BlitsDetail
