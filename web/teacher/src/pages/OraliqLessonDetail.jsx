import React from 'react'
import Navbar from '../components/Navbar'
import OraliqLessonDetailComponent from '../components/OraliqLessonDetailComponent'
import { Outlet, useLocation } from 'react-router-dom'
import { useCustomContext } from '../context/TestContext'
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { oraliqdarslar_db } from '../utils/dataLoader';


function OraliqLessonDetail() {
    const { oraliqLessontest, fetchOraliqLessonTest, Background, getTranslationValue } = useCustomContext();
    const params = useParams();
    // Dars banneri (admin'da yuklanadi) — savollardan oldin katta ko'rsatiladi
    const lesson = oraliqdarslar_db.find((item) => item.id == params.id);

    useEffect(() => {
        fetchOraliqLessonTest(params.id);
    }, [params.id]); // Correctly specify the dependency array here


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
                style={{
                    // margin: '1rem', 
                    // marginBottom:'0.5rem',
                    // minHeight:'84vh'
                }}
            >
                <OraliqLessonDetailComponent
                    key={params.id}
                    oraliqLessontest={{ oraliqLessontest }}
                    banner={lesson?.banner || ''}
                    lessonTitle={lesson ? getTranslationValue(lesson, 'name') : ''}
                />
                <Outlet />
            </div>
        </div>
    )
}

export default OraliqLessonDetail