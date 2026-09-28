import { createHashRouter } from "react-router-dom";
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

import Variantss from "../pages/Variants";

// Hash router: Electron `loadFile` (file://) da ham to'g'ri ishlaydi,
// nisbiy `./static-images/...` yo'llari doim index.html ga nisbatan.
// (Seoul'dagi `/C:/...` nusxalari shu sababli kerak emas.)
export const router = createHashRouter([
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
        path:'/blits/:blitsId/',
        element: <PrivateRoute><BlitsTest/></PrivateRoute>
    },
    {
        path:'/variants',
        element: <PrivateRoute><Variantss/></PrivateRoute>
    },
])
