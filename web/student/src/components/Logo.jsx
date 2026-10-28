import React from 'react';
import { useCustomContext } from '../context/TestContext';

function Logo() {
  const { bgLogo } = useCustomContext();

    return (
        <div className='h-full flex items-center'>
            <img src={bgLogo} className='h-16' alt="logo image" />
        </div>
    );
}

export default Logo;
