import React, { useEffect } from 'react'
import { useCustomContext } from '../context/TestContext'
import { Outlet, useParams } from 'react-router-dom';
import Loader from './Loader';
import SolveQuizComponent from './SolveQuizComponent';
import Navbar from './Navbar';

function VariantDetail() {
    const param = useParams();
    const { fetchVariant, variant, loading,Background } = useCustomContext();
    
    useEffect(() => { fetchVariant(param.id) }, []);
    if(loading) return <Loader />
    if (!variant || variant.length === 0|| variant[0].var_id!=param.id) return null
    const data= variant
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
            <div
                className="bg-gray-950/90 max-w-full min-h-full"
                style={{
                    // margin: '1rem', // Removed unnecessary margin
                    // marginBottom: '0.5rem',
                }}
            >
                <SolveQuizComponent data={data} />
                <Outlet />
            </div>
        </div>
    )
}

export default VariantDetail