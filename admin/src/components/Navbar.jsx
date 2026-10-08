import { useNavigate, useLocation } from 'react-router-dom';
import { useData } from '../context/DataContext';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ actionsRef, titleRef }) {
  const { lang, setLang, t } = useData();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isHome = location.pathname === '/';

  const handleLogout = async () => {
    if (confirm("Chiqishni xohlaysizmi?")) {
      await logout();
      navigate('/login');
    }
  };

  return (
    <nav className="flex items-center px-6 py-3 gap-4 shrink-0"
         style={{ background: 'rgba(10,14,26,0.7)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
      <div className="w-12 h-12 shrink-0 rounded-full flex items-center justify-center text-lg font-bold text-white cursor-pointer"
           style={{ background: 'linear-gradient(135deg, #1a3a6c, #2563eb)' }}
           onClick={() => navigate('/')} role="button">
        AT
      </div>

      {/* Sahifa sarlavhasi (masalan, savol sahifasida dars nomi) */}
      <div ref={titleRef} className="min-w-0 flex-[3] min-[1340px]:flex-none empty:hidden" />

      <div className="flex-1 min-w-0 text-center text-sm font-semibold uppercase tracking-widest whitespace-nowrap invisible min-[1340px]:visible" style={{ color: '#c8d6e5' }}>
        {t('home')}
      </div>

      <div className="flex gap-1.5 shrink-0">
        {['uz', 'ru', 'cry'].map(l => (
          <button key={l} onClick={() => setLang(l)}
            className={`px-4 py-1.5 text-sm font-semibold border cursor-pointer transition-all ${
              lang === l
                ? 'text-blue-400 border-blue-500'
                : 'text-slate-400 border-white/20 hover:bg-white/5'
            }`}
            style={lang === l ? { background: 'rgba(59,130,246,0.15)' } : { background: 'transparent' }}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>

      {!isHome && (
        <button onClick={() => navigate(-1)}
          className="px-4 py-1.5 text-sm text-slate-400 border border-white/15 cursor-pointer flex items-center gap-1.5 whitespace-nowrap shrink-0 transition-all hover:bg-white/5 hover:text-white"
          style={{ background: 'transparent' }}>
          ← <span className="hidden xl:inline">{t('back')}</span>
        </button>
      )}

      {/* Sahifaga xos tugmalar (masalan, savol sahifasidagi "Boshqa mavzu" va
          "Tahrirlash") shu yerga portal orqali chiqariladi. */}
      <div ref={actionsRef} className="flex items-center gap-2 shrink-0 whitespace-nowrap empty:hidden" />

      {user && (
        <div className="flex items-center gap-3 pl-2 border-l border-white/10 shrink-0 whitespace-nowrap">
          <div className="text-right hidden xl:block">
            <div className="text-xs font-medium text-white">{user.full_name || user.phone}</div>
            <div className="text-[10px] text-blue-400 uppercase tracking-wider">{user.role || 'admin'}</div>
          </div>
          <button
            onClick={handleLogout}
            title="Tizimdan chiqish"
            className="px-3 py-1.5 text-xs font-semibold border border-red-500/40 text-red-400 rounded cursor-pointer hover:bg-red-500/20 transition-all flex items-center gap-1"
          >
            🚪 Chiqish
          </button>
        </div>
      )}
    </nav>
  );
}
