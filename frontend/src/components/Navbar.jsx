import React, { useState } from 'react';
import Logo from './Logo';
import { NavLink } from 'react-router-dom';
import { LiaBarsSolid, LiaTimesSolid } from "react-icons/lia";
import { useCustomContext } from '../context/TestContext';
import Lang from './Lang';
import LogOut from './LogOut'; // Import the LogOut component

function Navbar() {
    const { active, setActive, getTranslation } = useCustomContext();
    const [showModal, setShowModal] = useState(false);
    const [code, setCode] = useState("");

    const handleLogOut = () => {
        if (code === 'Aramis') {
            window.Electron.ipcRenderer.send('app-close')
        } else {
            alert('Incorrect code');
        }
    };

    return (
        <nav className="py-2 h-16 shadow-md sticky top-0 z-0 bg-blue-800/10">
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
                        <Lang />
                        {/* LogOut component with rotated logout icon */}
                        <LogOut />
                        {/* Circular X Logout Button */}
                        <button
                            onClick={() => setShowModal(true)}
                            className="w-10 h-10 pl-6 flex items-center justify-center  text-white rounded-full"
                            title="Log Out"
                        >
                            <LiaTimesSolid className="text-2xl" />
                        </button>
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
                        {/* Circular X Logout Button */}
                        <button
                            onClick={() => setShowModal(true)}
                            className="w-10 h-10  flex pl-6 items-center justify-center  text-white rounded-full"
                            title="Log Out"
                        >
                            <LiaTimesSolid className="text-2xl" />
                        </button>
                    </div>
                </div>
            </div>


            {/* Modal for entering the logout code */}
            {showModal && (
                <div className="absolute inset-0 bg-gray-800 bg-opacity-50 flex items-center justify-center">
                    <div className="bg-white p-5 rounded shadow-lg">
                        <h2 className="text-xl mb-4">Enter Code to Log Out</h2>
                        <input
                            type="text"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            className="border p-2 w-full mb-4"
                            placeholder="Enter Code"
                        />
                        <button
                            onClick={handleLogOut}
                            className="bg-blue-500 text-white py-2 px-4 rounded">
                            Confirm
                        </button>
                        <button
                            onClick={() => setShowModal(false)}
                            className="ml-4 bg-gray-500 text-white py-2 px-4 rounded">
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </nav>
    );
}

export default Navbar;
