import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <>
      <div className="bg-wrap" />
      <div className="hex-pattern" />
      <div className="relative z-1 h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </div>
    </>
  );
}
