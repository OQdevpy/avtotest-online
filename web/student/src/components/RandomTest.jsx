import React, { useEffect } from 'react'
import SliderComponent from './SliderComponent'
import { useCustomContext } from '../context/TestContext'
import Loader from './Loader';
import { useNavigate } from 'react-router-dom';


function RandomTest() {
    const { randomTests, fetchRandomTests, loading } = useCustomContext();
    useEffect(() => { fetchRandomTests() }, []);
    if (loading) return <Loader />
    if (!randomTests || randomTests.length === 0) return null;

    return (
        <>
            <SliderComponent variant={randomTests} />
        </>
    )
}

export default RandomTest