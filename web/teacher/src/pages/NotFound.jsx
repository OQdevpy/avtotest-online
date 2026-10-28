import React from 'react';
import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom';

// Topilmagan manzil ham, sahifadagi xato ham shu yerda ko'rsatiladi. Xato matni
// chiqariladi — ilgari har qanday xato "404" bo'lib ko'rinardi va sababi
// noma'lum qolardi.
const NotFound = () => {
    const error = useRouteError();
    const notFound = !error || (isRouteErrorResponse(error) && error.status === 404);
    const message = error && !notFound
        ? (error.statusText || error.message || String(error))
        : null;

    return (
        <div className='h-screen flex items-center justify-center flex-col gap-5 bg-slate-900 text-white px-6 text-center'>
            <h1 className='text-5xl font-bold text-blue-300'>Ooops!</h1>
            <p className='text-2xl font-bold'>
                {notFound ? '404 — sahifa topilmadi' : 'Xatolik yuz berdi'}
            </p>
            {message && <p className='text-sm text-slate-400 max-w-xl break-words'>{message}</p>}
            <div className='flex gap-3'>
                <Link to="/" className='btn btn-neutral btn-outline text-white'>Bosh sahifa</Link>
                <button className='btn btn-outline text-white' onClick={() => window.location.reload()}>
                    Qayta yuklash
                </button>
            </div>
        </div>
    );
};

export default NotFound;
