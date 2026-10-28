import { createHashRouter } from "react-router-dom";
import NotFound from "../pages/NotFound";
import SignIn from "../pages/SignIn";
import PrivateRoute from "../utils/PrivateRoute";
import App from "../App";
import Lessons from "../pages/Lessons";
import LessonDetail from "../pages/LessonDetail";
import OraliqLessonDetail from "../pages/OraliqLessonDetail";
import BlitsDetail from "../pages/BlitsDetail";

// O'qituvchi ilovasi: faqat darslar va blits (test/imtihon/variantlar yo'q).
// Hash router: Electron `loadFile` (file://) da ham to'g'ri ishlaydi,
// nisbiy `./static-images/...` yo'llari doim index.html ga nisbatan.
const routes = [
    {
        path: '/',
        element: <PrivateRoute><App /></PrivateRoute>,
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
        path: "/blits/:id",
        element: <PrivateRoute><BlitsDetail /></PrivateRoute>,
    },
    {
        path: '/login',
        element: <SignIn />
    },
]

// Xato sahifasi har bir marshrutda; topilmagan manzil uchun ham shu sahifa (`*`).
export const router = createHashRouter([
    ...routes.map((route) => ({ ...route, errorElement: <NotFound /> })),
    { path: '*', element: <NotFound /> },
])
