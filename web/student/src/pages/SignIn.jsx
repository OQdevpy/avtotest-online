import { useEffect, useRef, useState } from 'react';
import { useAuth, savedCode } from '../context/AuthContext';
import Logo from '../components/Logo';
import { IoPhonePortraitOutline } from "react-icons/io5";
import { TbPasswordMobilePhone } from "react-icons/tb";
import { FaEye, FaEyeSlash } from "react-icons/fa";
import { useNavigate } from 'react-router-dom';

function SignIn() {
    const { handleChange, handleSubmit, loginWithCode, setPassword, isLoggedin, loading, password } = useAuth();
    const navigate = useNavigate();
    const [showCode, setShowCode] = useState(false);
    const autoTried = useRef(false);

    // Saqlangan kod bo'lsa — qayta yozdirmasdan o'zi kiradi (bir marta)
    useEffect(() => {
        if (autoTried.current) return;
        autoTried.current = true;
        if (isLoggedin) {
            navigate('/', { replace: true });
            return;
        }
        savedCode.load().then((code) => {
            if (!code) return;
            setPassword(code);
            loginWithCode(code, (path) => navigate(path));
        });
    }, []);

    return (
        <div className='flex items-center justify-center h-screen container mx-auto'>
            <form
                onSubmit={(data) => handleSubmit(data, (path) => navigate(path))}
                className='basis-[400px] flex flex-col gap-4 shadow-md py-6 px-4 relative'>
                <div className='w-36 mx-auto'>
                    <Logo />
                </div>
                <label className="input input-bordered flex items-center gap-2">
                    <div>
                        <TbPasswordMobilePhone size={20} color='grey' />
                    </div>
                    <input
                        type={showCode ? "text" : "password"}
                        className="grow"
                        placeholder='Token'
                        id='password'
                        value={password}
                        onChange={handleChange}
                        required />
                    <button
                        type="button"
                        onClick={() => setShowCode((prev) => !prev)}
                        title={showCode ? "Yashirish" : "Ko'rsatish"}
                        className="text-gray-400 hover:text-gray-200"
                    >
                        {showCode ? <FaEyeSlash size={18} /> : <FaEye size={18} />}
                    </button>
                </label>

                <button type='submit' disabled={loading} className="px-4 py-2 rounded-sm text-white bg-blue-800 block mx-auto uppercase mt-5 disabled:opacity-60">Kirish</button>
            </form >
        </div>
    )
}

export default SignIn
