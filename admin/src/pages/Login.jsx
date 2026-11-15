import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { useAuth } from '../context/AuthContext';
import { startTelegram, telegramStatus } from '../services/api';

const POLL_MS = 2000;

// Shef paneli — kirish faqat Telegram orqali: havola (yoki QR) botni ochadi,
// shef kontaktini yuboradi, sahifa o'zi kiradi. Parol yo'q.
export default function Login() {
  const [session, setSession] = useState(null); // {token, link}
  const [status, setStatus] = useState('idle'); // idle | pending | verified | expired | mismatch
  const [error, setError] = useState('');
  const { loginWithTelegram } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const done = useRef(false);

  const begin = async () => {
    setError('');
    done.current = false;
    try {
      const data = await startTelegram();
      setSession({ token: data.token, link: data.link });
      setStatus('pending');
      window.open(data.link, '_blank', 'noopener');
    } catch (err) {
      setError(err.status === 429 ? "Juda ko'p urinish. Birozdan so'ng qayta urinib ko'ring."
        : err.message);
    }
  };

  const check = useCallback(async () => {
    if (!session || done.current) return;
    const next = await telegramStatus(session.token).catch(() => 'pending');
    if (next !== 'verified') {
      if (next !== 'pending') setStatus(next);
      return;
    }
    done.current = true;
    setStatus('verified');
    try {
      await loginWithTelegram(session.token);
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err) {
      setStatus('expired');
      if (err.code === 'blocked') setError('Hisob bloklangan.');
      else if (err.code === 'device_limit') setError('Ushbu hisob boshqa qurilmada ochiq. Avval u qurilmadan chiqing.');
      else setError(err.message);
    }
  }, [session, loginWithTelegram, location, navigate]);

  useEffect(() => {
    if (status !== 'pending') return undefined;
    const id = setInterval(check, POLL_MS);
    return () => clearInterval(id);
  }, [status, check]);

  const waiting = status === 'pending' || status === 'verified';

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
      <div className="max-w-md w-full bg-gray-800 rounded-lg shadow-lg p-8">
        <h2 className="text-3xl font-bold text-center text-white mb-8">Admin Panel</h2>
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 rounded p-3 mb-6 text-sm text-center">
            {error}
          </div>
        )}
        {status === 'mismatch' && !error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 rounded p-3 mb-6 text-sm text-center">
            Faqat O'zbekiston raqami (+998) bilan kirish mumkin.
          </div>
        )}
        {status === 'expired' && !error && (
          <div className="bg-red-500/10 border border-red-500 text-red-500 rounded p-3 mb-6 text-sm text-center">
            Vaqt tugadi. Qaytadan urinib ko'ring.
          </div>
        )}

        {waiting && session ? (
          <div className="space-y-5 text-center">
            <p className="text-gray-300 text-sm">
              Telefoningizda QR kodni skanerlang yoki havolani oching va botda
              «Kontaktni ulashish» tugmasini bosing.
            </p>
            <div className="bg-white p-4 rounded inline-block">
              <QRCodeSVG value={session.link} size={200} />
            </div>
            <a href={session.link} target="_blank" rel="noopener noreferrer"
               className="block text-blue-400 hover:text-blue-300 text-sm break-all">
              {session.link}
            </a>
            <p className="text-gray-400 text-sm">
              {status === 'verified' ? 'Tasdiqlandi, kirilmoqda…' : 'Telegram tasdig\'i kutilmoqda…'}
            </p>
            <button type="button" onClick={() => { setSession(null); setStatus('idle'); }}
                    className="text-gray-400 hover:text-white text-sm">
              Bekor qilish
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={begin}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors"
          >
            {status === 'idle' ? 'Telegram orqali kirish' : 'Qaytadan urinish'}
          </button>
        )}
      </div>
    </div>
  );
}
