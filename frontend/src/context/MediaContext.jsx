import { createContext, useContext, useEffect, useState } from 'react';

const MediaContext = createContext(null);
const ContextProvider = ({ children }) => {
    const URL = import.meta.env.VITE_MEDIA_BASE_URL;
    const DefaultImge = URL+'/static-images/default_image.jpg'
    const background = URL+'/static-images/romo-sagan-thumb.jpg'
    const logo = URL + '/static-images/removebg.png'
    

    return (
        <MediaContext.Provider
            value={{
                DefaultImge,
                background,
                logo
            }}
        >
            {children}
        </MediaContext.Provider>
    )
}

const useCustomContext = () => useContext(MediaContext)

export { ContextProvider, useCustomContext }
