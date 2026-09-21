import { createBrowserRouter } from "react-router-dom";
import NotFound from "../pages/NotFound";
import VariantDetail from "../components/VariantDetail";
import RandomTest from "../components/RandomTest";
import SignIn from "../pages/SignIn";
import PrivateRoute from "../utils/PrivateRoute";
import App from "../App";
import Layout from "../pages/Layout";
import Variants from "../pages/Variants";
import Lessons from "../pages/Lessons";
import LessonDetail from "../pages/LessonDetail";
import OraliqLessonDetail from "../pages/OraliqLessonDetail";
import SolveQuiz from "../pages/SolveQuiz";
import OraliqTest from "../pages/OraliqTest";
import OraliqTestDetail from "../pages/OraliqTestDetail";
import SolveOraliqTest from "../pages/SolveOraliqTest";
import SolveTest from "../pages/SolveTest";
import BlitsTest from "../pages/BlitsTest";
import Blits2Test from "../pages/Blits2Test";
import Blits3Test from "../pages/Blits3Test";

import Variantss from "../pages/Variants";

export const router = createBrowserRouter([
    {
        path: '/',
        element: <PrivateRoute><App /></PrivateRoute>,
        errorElement: <NotFound />
    },

    {
        path: "/variants",
        element: <PrivateRoute><Variants />,</PrivateRoute>,

    },
    {
        path: "/lessons",
        element: <PrivateRoute><Lessons /></PrivateRoute>,
    },
    {
        path: "/lessons/:id",
        element: <PrivateRoute><LessonDetail /></PrivateRoute>,
    },
    {
        path: "/lesson-detail/:id",
        element: <PrivateRoute><OraliqLessonDetail /></PrivateRoute>,
    },

    {
        path: "/solve-quiz",
        element: <PrivateRoute><SolveQuiz /></PrivateRoute>,
    },


    

    {
        path: "/variants/:id",
        element: <PrivateRoute><VariantDetail /></PrivateRoute>
    },



    {
        path: '/login',
        element: <SignIn />
    },

    {
        path: '/oraliq-test',
        element: <PrivateRoute><OraliqTest /></PrivateRoute>
    },
    {
        path: '/oraliq-test/:id',
        element: <PrivateRoute><OraliqTestDetail /></PrivateRoute>
    },

    {
        path: '/solve-oraliq/:count/:id/',
        element: <PrivateRoute><SolveOraliqTest /></PrivateRoute>
    },
    {
        path:'/solve-test/',
        element: <PrivateRoute><OraliqTestDetail/></PrivateRoute>
    },
    {
        path:'/solve-test/:count/',
        element: <PrivateRoute><SolveTest/></PrivateRoute>
    },
    {
        path:'/blits/',
        element: <PrivateRoute><BlitsTest/></PrivateRoute>
    },
    {
        path:'/blits2/',
        element: <PrivateRoute><Blits2Test/></PrivateRoute>
    },
    {
        path:'/blits3/',
        element: <PrivateRoute><Blits3Test/></PrivateRoute>
    },
    {
        path:'/variants',
        element: <PrivateRoute><Variantss/></PrivateRoute>
    },
    {
        path: '/C:/',
        element: <PrivateRoute><App /></PrivateRoute>,
        errorElement: <NotFound />
    },
    {
        path: "/C:/variants",
        element: <PrivateRoute><Variants /></PrivateRoute>,
    },
    {
        path: "/C:/lessons",
        element: <PrivateRoute><Lessons /></PrivateRoute>,
    },
    {
        path: "/C:/lessons/:id",
        element: <PrivateRoute><LessonDetail /></PrivateRoute>,
    },
    {
        path: "/C:/lesson-detail/:id",
        element: <PrivateRoute><OraliqLessonDetail /></PrivateRoute>,
    },
    {
        path: "/C:/solve-quiz",
        element: <PrivateRoute><SolveQuiz /></PrivateRoute>,
    },
    {
        path: "/C:/variants/:id",
        element: <PrivateRoute><VariantDetail /></PrivateRoute>
    },
    {
        path: '/C:/oraliq-test',
        element: <PrivateRoute><OraliqTest /></PrivateRoute>
    },
    {
        path: '/C:/oraliq-test/:id',
        element: <PrivateRoute><OraliqTestDetail /></PrivateRoute>
    },
    {
        path: '/C:/solve-oraliq/:count/:id/',
        element: <PrivateRoute><SolveOraliqTest /></PrivateRoute>
    },
    {
        path: '/C:/solve-test/',
        element: <PrivateRoute><OraliqTestDetail /></PrivateRoute>
    },
    {
        path: '/C:/solve-test/:count/',
        element: <PrivateRoute><SolveTest /></PrivateRoute>
    },
    {
        path:'/C:/blits/',
        element: <PrivateRoute><BlitsTest/></PrivateRoute>
    },
    {
        path:'/C:/blits2/',
        element: <PrivateRoute><Blits2Test/></PrivateRoute>
    },
    {
        path:'/C:/blits3/',
        element: <PrivateRoute><Blits3Test/></PrivateRoute>
    },
    {
        path: '/C:/variants',
        element: <PrivateRoute><Variantss /></PrivateRoute>
    },
    



])