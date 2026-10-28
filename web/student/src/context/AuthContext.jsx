import { createContext, useState, useContext, useEffect } from "react";
import { toast } from "react-toastify";
import { apiFetch, getDeviceId, isElectron, onSessionExpired, tokens } from "../api/client";
import { resetData } from "../utils/dataLoader";

const AuthContext = createContext(null);

// Bir marta kiritilgan kirish kodi shu kompyuterda saqlanadi: sessiya tugasa
// ham (refresh muddati, ilova yangilanib xotira tozalansa) kod qayta
// yozilmaydi — login sahifasi u bilan o'zi kiradi. Desktopda kod faylga ham
// yoziladi (main.cjs), chunki yangi versiya localStorage'ni tozalaydi.
const CODE_KEY = 'quizCode';
export const savedCode = {
    get() { return localStorage.getItem(CODE_KEY) || ''; },
    set(code) {
        localStorage.setItem(CODE_KEY, code);
        window.Electron?.setSavedCode?.(code);
    },
    clear() {
        localStorage.removeItem(CODE_KEY);
        window.Electron?.setSavedCode?.('');
    },
    async load() {
        let code = savedCode.get();
        if (!code && window.Electron?.getSavedCode) {
            code = (await window.Electron.getSavedCode()) || '';
            if (code) localStorage.setItem(CODE_KEY, code);
        }
        return code;
    },
};

export const AuthProvider = ({ children }) => {
    const [isLoggedin, setIsLoggedin] = useState(Boolean(tokens.access || tokens.refresh));

    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        password: savedCode.get()
    });


    const { password } = formData;

    // Refresh ham o'tmasa (kod muddati tugagan, qurilma uzilgan) — login sahifasi
    useEffect(() => onSessionExpired(() => {
        setIsLoggedin(false);
        // Saqlangan kod bo'lsa login sahifasi o'zi qayta kiradi
        if (!savedCode.get()) toast.warning('Sessiya tugadi. Kodni qayta kiriting.');
    }), []);

    const setPassword = (value) => setFormData((prev) => ({ ...prev, password: value }));

    const handleChange = (e) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.id]: e.target.value
        }))
    }

    // Shef bergan kirish kodi bilan kirish
    const loginWithCode = async (code, fn) => {
        setLoading(true);

        try {
            const electron = isElectron();
            const data = await apiFetch('/auth/login-code/', {
                method: 'POST',
                auth: false,
                body: {
                    code,
                    platform: electron ? 'desktop' : 'web',
                    device_label: `${electron ? 'AvtoQuiz' : 'Brauzer'} / ${navigator.platform || ''}`.trim(),
                    device_id: await getDeviceId(),
                },
            });
            tokens.set(data.tokens);
            savedCode.set(code);
            resetData();
            setIsLoggedin(true);
            fn('/');
            toast.success('Hush kelibsiz.');
        } catch (error) {
            // Kod rad etildi (nofaol, boshqa kompyuterga biriktirilgan...) —
            // saqlangani o'chiriladi. Tarmoq xatosida kod qoladi.
            if (error.status) {
                savedCode.clear();
                setFormData({ password: '' });
            }
            toast.error(error.message || 'Server bilan aloqa yo\'q');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = (e, fn) => {
        e.preventDefault();
        return loginWithCode(password.trim(), fn);
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
        savedCode.clear();
        setFormData({ password: '' });
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
            setPassword,
            handleSubmit,
            loginWithCode,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => useContext(AuthContext);
