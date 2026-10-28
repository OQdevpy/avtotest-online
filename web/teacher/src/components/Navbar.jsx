import React from 'react';
import Logo from './Logo';
import { NavLink } from 'react-router-dom';
import { LiaBarsSolid, LiaTimesSolid } from "react-icons/lia";
import { useCustomContext } from '../context/TestContext';
import Lang from './Lang';
import UpdatedDate from './UpdatedDate';
import LogOut from './LogOut'; // Import the LogOut component

function Navbar() {
    const { active, setActive, getTranslation } = useCustomContext();
    return (
        <nav className="py-2 h-16 shadow-md sticky top-0 z-50 bg-blue-800/30 backdrop-blur-sm">
            <div className="container flex items-center justify-between h-full">
                <div className='w-28 h-full flex items-center'>
                    <Logo />
                </div>
                <div className="hidden md:flex grow justify-center gap-5">
                    <NavLink to='/' className={`flex items-center uppercase text-white font-semibold`}>
                        {active && getTranslation('dashboard')}
                    </NavLink>
                </div>

                <div className="flex items-center gap-4">
                    <div className='hidden md:flex gap-4'>
                        <UpdatedDate />
                        <Lang />
                        {/* LogOut component with rotated logout icon */}
                        <LogOut />
                    </div>
                    <button
                        onClick={() => setActive(!active)}
                        className='btn btn-link md:hidden'>
                        {active ? <LiaTimesSolid className="text-3xl text-white" /> : <LiaBarsSolid className="text-3xl text-white" />}
                    </button>
                </div>
            </div>

            {/* Mobile menu */}
            <div className={`${active ? 'h-0 ' : 'h-[150px]'} overflow-hidden origin-top duration-200 absolute w-full bottom-0 translate-y-full bg-white shadow-md rounded-b-lg md:hidden`}>
                <div className="container flex flex-col gap-5">
                    <div className="flex flex-col justify-center gap-5 items-start">
                        <NavLink
                            onClick={() => setActive(!active)}
                            to='/' className={`flex items-center uppercase text-white font-semibold`}>
                            {getTranslation('dashboard')}
                        </NavLink>
                    </div>

                    <div className='flex gap-5 items-center justify-between'>
                        <Lang />
                        {/* LogOut component for mobile view */}
                        <LogOut />
                    </div>
                </div>
            </div>
        </nav>
    );
}

export default Navbar;
