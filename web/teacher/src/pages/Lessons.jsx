import { Outlet } from "react-router-dom"
import Navbar from "../components/Navbar"
import LessonListComponent from "../components/LessonList";
import { useCustomContext } from '../context/TestContext'
import { useEffect } from "react";


function Lessons() {
    const { oraliq, fetchOraliq, blits, fetchBlits, Background } = useCustomContext();
    useEffect(() => { fetchOraliq(); fetchBlits(); }, []);
    const path = "/lessons";
    return (
        <div
            style={{
                backgroundImage: `url(${Background})`,
                backgroundSize: 'cover',  // Ensures the image covers the entire container
                backgroundRepeat: 'no-repeat',  // Prevents the image from repeating
                backgroundAttachment: 'fixed',  // Keeps the background image fixed when scrolling
                height: '100vh',  // Ensure the container takes full viewport height
                margin: 0,  // Remove default margin
                padding: 0,  // Remove default padding
                overflow: 'hidden'  // Prevent overflow
            }}>
            <Navbar />
            <div style={
                {
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "flex-start",
                    height: "calc(100vh - 4rem)",
                    paddingTop: "2rem",
                    paddingBottom: "2rem",
                    overflowY: "auto",
                }
            }>
                <LessonListComponent oraliq={oraliq} blits={blits} path={path} />
                <Outlet />
            </div>
        </div>
    )
}

export default Lessons