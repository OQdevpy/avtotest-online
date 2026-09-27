import { useNavigate } from 'react-router-dom';
import { useData } from '../context/DataContext';

export default function Home() {
  const navigate = useNavigate();
  const { t } = useData();

  return (
    <div className="flex items-center justify-center h-full px-6">
      <div className="flex gap-8 flex-wrap justify-center">
        <div onClick={() => navigate('/sections')}
          className="w-70 h-55 rounded-2xl cursor-pointer flex flex-col items-center justify-center gap-4 text-white text-xl font-semibold transition-all hover:-translate-y-1.5"
          style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)', boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
          <span className="text-6xl">📚</span>
          <span>{t('lessons')}</span>
        </div>
        <div onClick={() => navigate('/blits')}
          className="w-70 h-55 rounded-2xl cursor-pointer flex flex-col items-center justify-center gap-4 text-white text-xl font-semibold transition-all hover:-translate-y-1.5"
          style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)', boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
          <span className="text-6xl">⚡</span>
          <span>{t('blits')}</span>
        </div>
      </div>
    </div>
  );
}
