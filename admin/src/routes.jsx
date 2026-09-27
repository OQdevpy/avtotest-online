import React from 'react';
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Sections from './pages/Sections';
import Lessons from './pages/Lessons';
import QuestionDetail from './pages/QuestionDetail';
import BlitsPage from './pages/BlitsPage';
import Login from './pages/Login';
import { useAuth } from './context/AuthContext';

function ProtectedRoute() {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Home /> },
          { path: 'sections', element: <Sections /> },
          { path: 'sections/:sectionId/lessons', element: <Lessons /> },
          { path: 'sections/:sectionId/lessons/:lessonId/questions', element: <QuestionDetail /> },
          { path: 'blits', element: <BlitsPage /> },
        ],
      },
    ],
  },
]);
