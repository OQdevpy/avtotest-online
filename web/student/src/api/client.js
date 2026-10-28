// Backend bilan yagona aloqa nuqtasi (web versiyasi): JWT, `?compat=1`, 401 da
// bir marta token yangilash, sessiya tugasa — tinglovchilarga xabar.
//
// Desktopdan farqi: so'rovlar to'g'ridan-to'g'ri API'ga emas, shifrlangan
// kanal orqali ketadi (./secure.js) — Network oynasida ma'lumot ko'rinmaydi.

import { secureRequest } from './secure';

const ACCESS_KEY = 'quizAccess';
const REFRESH_KEY = 'quizRefresh';

// Ilova tillari (uz | ru | cry) → backend `?lang=` qiymatlari
export const API_LANG = { uz: 'uz', ru: 'ru', cry: 'kr' };

export const tokens = {
    get access() { return localStorage.getItem(ACCESS_KEY); },
    get refresh() { return localStorage.getItem(REFRESH_KEY); },
    set({ access, refresh }) {
        if (access) localStorage.setItem(ACCESS_KEY, access);
        if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    },
    clear() {
        localStorage.removeItem(ACCESS_KEY);
        localStorage.removeItem(REFRESH_KEY);
    },
};

// Sessiya tugaganda (refresh ham o'tmasa) AuthContext login sahifasiga qaytaradi
const expiredListeners = new Set();
export function onSessionExpired(fn) {
    expiredListeners.add(fn);
    return () => expiredListeners.delete(fn);
}

export class ApiError extends Error {
    constructor(status, message, data) {
        super(message);
        this.status = status;
        this.data = data;
    }
}

// Web versiya — desktop emas
export function isElectron() {
    return false;
}

// Brauzer ID'si — kirish kodi shu brauzerga biriktiriladi (bir marta yaratiladi).
const DEVICE_KEY = 'quizDeviceId';
export async function getDeviceId() {
    let id = localStorage.getItem(DEVICE_KEY);
    if (!id) {
        id = (crypto.randomUUID() + crypto.randomUUID()).replace(/-/g, '');
        localStorage.setItem(DEVICE_KEY, id);
    }
    return id;
}

function buildQuery(query = {}) {
    const params = { compat: '1' };
    for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null && value !== '') {
            params[key] = String(value);
        }
    }
    return params;
}

let refreshPromise = null;
async function refreshAccess() {
    if (!tokens.refresh) return false;
    if (!refreshPromise) {
        refreshPromise = (async () => {
            try {
                const res = await secureRequest({
                    method: 'POST',
                    path: '/auth/token/refresh/',
                    query: buildQuery(),
                    body: { refresh: tokens.refresh },
                });
                if (res.status !== 200) return false;
                // ROTATE_REFRESH_TOKENS yoqilgan — yangi refresh ham keladi
                tokens.set(res.data);
                return true;
            } catch {
                return false;
            } finally {
                refreshPromise = null;
            }
        })();
    }
    return refreshPromise;
}

export async function apiFetch(path, { method = 'GET', query, body, auth = true } = {}) {
    const send = () => secureRequest({
        method,
        path,
        query: buildQuery(query),
        body: body === undefined ? null : body,
        token: auth ? tokens.access : null,
    });

    let res = await send();
    if (res.status === 401 && auth && tokens.refresh && await refreshAccess()) {
        res = await send();
    }
    if (res.status === 401 && auth) {
        // Parallel so'rovlar ham 401 oladi — xabar faqat bir marta
        const hadSession = Boolean(tokens.access || tokens.refresh);
        tokens.clear();
        if (hadSession) expiredListeners.forEach((fn) => fn());
    }

    if (res.status < 200 || res.status >= 300) {
        const message = res.data?.detail || res.data?.error || `Server xatosi (${res.status})`;
        throw new ApiError(res.status, message, res.data);
    }
    return res.data;
}

// Sahifalangan ro'yxatning barcha sahifalari (`{results, next}`)
export async function fetchAllPages(path, query = {}) {
    const items = [];
    let page = 1;
    for (;;) {
        const data = await apiFetch(path, { query: { ...query, page, page_size: 200 } });
        if (Array.isArray(data)) return data;
        items.push(...data.results);
        if (!data.next) return items;
        page += 1;
    }
}
