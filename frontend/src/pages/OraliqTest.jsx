import { Outlet } from "react-router-dom"
import LessonListComponent from "../components/LessonList";
import { useCustomContext } from '../context/TestContext'
import { useEffect } from "react";
import { toast } from "react-toastify";
import Navbar from "../components/Navbar";


function OraliqTest() {
    const { oraliq, fetchOraliq,Background } = useCustomContext();
    useEffect(() => { fetchOraliq() }, []);

    const path = "/solve-oraliq/20";

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
                    justifyContent: "center",
                    height: "80vh",
                }
            }>
                <LessonListComponent oraliq={oraliq} path={path} />

                <Outlet />
            </div>
        </div>
    )
}

export default OraliqTest