import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { checkForUpdates, isDataLoaded, loadAllData } from "./dataLoader";
import Loader from "../components/Loader";

// Kirilgan bo'lsa — avval barcha ma'lumot API'dan bir marta yuklanadi,
// keyin sahifa ko'rsatiladi (seoul'da ma'lumot ishga tushishda tayyor edi).
const PrivateRoute = ({ children }) => {
  const { isLoggedin } = useAuth();
  const { pathname } = useLocation();
  const [ready, setReady] = useState(isDataLoaded());
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  // Har bir sahifaga kirilganda (masalan, mavzudan chiqib qayta kirilganda)
  // serverdagi versiya solishtiriladi: o'zgargan bo'lsa ma'lumot qayta
  // yuklanadi va sahifa yangi savollar bilan qayta chiziladi.
  // `pathname` ga bog'langan: React Router sahifa almashganda shu komponentni
  // qayta yaratmaydi (turi bir xil), shuning uchun mount'ga ishonib bo'lmaydi.
  useEffect(() => {
    if (!isLoggedin || !isDataLoaded()) return;
    // `active` bayrog'i ataylab yo'q: tez sahifa almashsa ham ma'lumot
    // "eskirgan" deb belgilangan bo'lsa, qayta yuklash albatta boshlanishi kerak.
    checkForUpdates().then((changed) => {
      if (changed) setReady(false);
    });
  }, [isLoggedin, pathname]);

  useEffect(() => {
    if (!isLoggedin || ready) return;
    let active = true;
    setError(null);
    loadAllData()
      .then(() => active && setReady(true))
      .catch((err) => active && setError(err.message || "Ma'lumot yuklanmadi"));
    return () => { active = false; };
  }, [isLoggedin, ready, attempt]);

  if (!isLoggedin) return <Navigate to="/login" replace={true} />;
  if (ready) return children;

  return (
    <div className="flex flex-col items-center justify-center h-screen gap-4 text-white">
      {error ? (
        <>
          <p className="text-lg text-center px-4">{error}</p>
          <button
            className="px-4 py-2 rounded-sm text-white bg-blue-800 uppercase"
            onClick={() => setAttempt((n) => n + 1)}
          >
            Qayta urinish
          </button>
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default PrivateRoute;
