import { createContext, useState, useContext, useEffect } from "react";
import { toast } from "react-toastify";
import { apiFetch, isElectron, onSessionExpired, tokens } from "../api/client";
import { resetContentCache } from "../api/content";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [isLoggedin, setIsLoggedin] = useState(Boolean(tokens.access || tokens.refresh));

    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        password: ''
    });


    const { password } = formData;

    // Refresh ham o'tmasa (kod muddati tugagan, qurilma uzilgan) — login sahifasi
    useEffect(() => onSessionExpired(() => {
        setIsLoggedin(false);
        toast.warning('Sessiya tugadi. Kodni qayta kiriting.');
    }), []);

    const handleChange = (e) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.id]: e.target.value
        }))
    }

    // Shef bergan kirish kodi bilan kirish
    const handleSubmit = async (e, fn) => {
        e.preventDefault();
        setLoading(true);

        try {
            const electron = isElectron();
            const data = await apiFetch('/auth/login-code/', {
                method: 'POST',
                auth: false,
                body: {
                    code: password.trim(),
                    platform: electron ? 'desktop' : 'web',
                    device_label: `${electron ? 'AvtoQuiz' : 'Brauzer'} / ${navigator.platform || ''}`.trim(),
                },
            });
            tokens.set(data.tokens);
            resetContentCache();
            setIsLoggedin(true);
            setFormData({ password: '' });
            fn('/');
            toast.success('Hush kelibsiz.');
        } catch (error) {
            toast.error(error.message || 'Server bilan aloqa yo\'q');
        } finally {
            setLoading(false);
        }
    };

    // Chiqish — serverdagi qurilma slotini ham bo'shatadi
    const logout = async () => {
        try {
            if (tokens.refresh) {
                await apiFetch('/auth/logout/', { method: 'POST', body: { refresh: tokens.refresh } });
            }
        } catch (error) {
            console.error(error);
        }
        tokens.clear();
        setIsLoggedin(false);
        toast.warning('Profildan chiqib ketdingiz.');
    }


    return (
        <AuthContext.Provider value={{
            isLoggedin,
            loading,
            formData,
            password,
            handleChange,
            handleSubmit,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext);
