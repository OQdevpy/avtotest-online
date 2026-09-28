// Backend bilan yagona aloqa nuqtasi: JWT (Bearer), `?compat=1`, 401 da bir
// marta token yangilash, sessiya tugasa — tinglovchilarga xabar.

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

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
        localStorage.removeItem('quizToken'); // eski web tokeni
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

export function isElectron() {
    return Boolean(window.Electron?.isDesktop) || navigator.userAgent.includes('Electron');
}

function buildUrl(path, query = {}) {
    const url = new URL(path.startsWith('http') ? path : `${API_URL}${path}`);
    url.searchParams.set('compat', '1');
    for (const [key, value] of Object.entries(query)) {
        if (value !== undefined && value !== null && value !== '') {
            url.searchParams.set(key, value);
        }
    }
    return url.toString();
}

let refreshPromise = null;
async function refreshAccess() {
    if (!tokens.refresh) return false;
    if (!refreshPromise) {
        refreshPromise = (async () => {
            try {
                const res = await fetch(buildUrl('/auth/token/refresh/'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh: tokens.refresh }),
                });
                if (!res.ok) return false;
                // ROTATE_REFRESH_TOKENS yoqilgan — yangi refresh ham keladi
                tokens.set(await res.json());
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
    const send = () => {
        const headers = { Accept: 'application/json' };
        if (body !== undefined) headers['Content-Type'] = 'application/json';
        if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;
        return fetch(buildUrl(path, query), {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    };

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

    const data = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) {
        const message = data?.detail || data?.error || `Server xatosi (${res.status})`;
        throw new ApiError(res.status, message, data);
    }
    return data;
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
