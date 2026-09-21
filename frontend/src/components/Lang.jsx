import React from 'react';
import { useCustomContext } from '../context/TestContext';

function Lang() {
    const { lang, changeLang } = useCustomContext();

    const languages = ['uz', 'ru', 'cry'];

    return (
        <div className="flex gap-2">
            {languages.map((language) => (
                <div
                    key={language}
                    className="flex items-center border border-blue-900 p-2 cursor-pointer h-10" // Set a fixed height for the div
                    onClick={() => changeLang(language)}
                >
                    <span
                        className={`w-2 ${
                            lang === language ? 'bg-green-500':''
                        }`}
                        style={{ height: '100%' }} // Set span height to 100%
                    ></span>
                    <span className={`ml-2 text-white font-semibold`}>
                        {language.toUpperCase()}
                    </span>
                    <span className='w-2'></span>
                </div>
            ))}
        </div>
    );
}

export default Lang;
