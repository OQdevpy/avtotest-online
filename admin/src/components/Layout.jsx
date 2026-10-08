import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  // Navbar'dagi sahifaga xos joylar (sarlavha va tugmalar) — sahifalar unga portal qiladi
  const [navbarSlot, setNavbarSlot] = useState(null);
  const [navbarTitleSlot, setNavbarTitleSlot] = useState(null);

  return (
    <>
      <div className="bg-wrap" />
      <div className="hex-pattern" />
      <div className="relative z-1 h-screen flex flex-col">
        <Navbar actionsRef={setNavbarSlot} titleRef={setNavbarTitleSlot} />
        <div className="flex-1 overflow-y-auto">
          <Outlet context={{ navbarSlot, navbarTitleSlot }} />
        </div>
      </div>
    </>
  );
}
