// Asosiy API manzili
const API_BASE = '/api/v1';

// Tokenlarni boshqarish — access xotirada (o'zgaruvchida), refresh localStorage'da
let accessToken = null;

export function setTokens({ access, refresh }) {
  accessToken = access;
  if (refresh) localStorage.setItem('avtotest_refresh', refresh);
}

export function clearTokens() {
  accessToken = null;
  localStorage.removeItem('avtotest_refresh');
}

export function getRefreshToken() {
  return localStorage.getItem('avtotest_refresh');
}

// Asosiy fetch wrapper — JWT bearer header qo'shadi, 401 da token yangilaydi
async function apiFetch(url, options = {}) {
  // URL to'liq yo'lga aylantirish
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  
  // Default headerlar
  const headers = { ...options.headers };
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  // Content-Type faqat FormData bo'lmasa qo'shiladi
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let response = await fetch(fullUrl, { ...options, headers });

  // 401 — token eskirgan, yangilashga urinib ko'ramiz
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      response = await fetch(fullUrl, { ...options, headers });
    }
  }

  return response;
}

// Token yangilash
export async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const data = await res.json();
    setTokens({ access: data.access, refresh: data.refresh || refresh });
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export async function login(phone, password) {
  const res = await apiFetch('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ phone, password, platform: 'web', device_label: 'Admin Panel' }),
  });
  
  if (!res.ok) {
    if (res.status === 403) throw new Error('Boshqa qurilmadan chiqing yoki kuting');
    if (res.status === 429) throw new Error('Kirish cheklangan. Keyinroq urinib ko\\'ring');
    throw new Error('Telefon yoki parol noto\\'g\\'ri');
  }
  
  const data = await res.json();
  setTokens(data.tokens);
  return data;
}

export async function logout() {
  const refresh = getRefreshToken();
  if (refresh) {
    await apiFetch('/auth/logout/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    }).catch(() => {});
  }
  clearTokens();
}

export async function fetchJSON(url) {
  const res = await apiFetch(url);
  if (!res.ok) throw new Error(`Fetch xatosi: ${res.status}`);
  return res.json();
}

export async function postJSON(url, data) {
  const res = await apiFetch(url, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Post xatosi: ${res.status}`);
  return res.json();
}

export async function patchJSON(url, data) {
  const res = await apiFetch(url, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Patch xatosi: ${res.status}`);
  return res.json();
}

export async function deleteResource(url) {
  const res = await apiFetch(url, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Delete xatosi: ${res.status}`);
  if (res.status !== 204) {
    try { return await res.json(); } catch { return null; }
  }
  return null;
}

export async function uploadFile(url, file, fieldName = 'file') {
  const formData = new FormData();
  formData.append(fieldName, file);
  const res = await apiFetch(url, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Yuklash xatosi: ${res.status}`);
  return res.json();
}
