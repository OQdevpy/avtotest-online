// Backend bilan shifrlangan kanal (backend: common/tunnel.py).
//
// Har bir API so'rovi bitta shifrlangan konvert bo'lib `POST /api/v1/s/` ga
// boradi: Network oynasida endpoint, parametrlar, token va javob ko'rinmaydi —
// faqat o'qib bo'lmaydigan baytlar.
//
// Kalit: ECDH (P-256) + HKDF-SHA256 → AES-256-GCM. Brauzer har sahifa
// yuklanganda yangi kalit juftligini yaratadi; maxfiy qismi eksport qilib
// bo'lmaydigan (non-extractable) CryptoKey bo'lib xotirada turadi.
// WebCrypto faqat HTTPS (yoki localhost) da ishlaydi.

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
const INFO = new TextEncoder().encode('avtotest-web-v1');
const IV_LEN = 12;

let sessionPromise = null;

function fromBase64Url(text) {
    const base64 = text.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4));
    return Uint8Array.from(binary, (ch) => ch.charCodeAt(0));
}

async function createSession() {
    const res = await fetch(`${API_URL}/s/key/`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Server xatosi (${res.status})`);
    const { k } = await res.json();
    const { subtle } = crypto;
    const serverKey = await subtle.importKey(
        'raw', fromBase64Url(k), { name: 'ECDH', namedCurve: 'P-256' }, false, [],
    );
    const pair = await subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits']);
    const pub = new Uint8Array(await subtle.exportKey('raw', pair.publicKey));
    const shared = await subtle.deriveBits({ name: 'ECDH', public: serverKey }, pair.privateKey, 256);
    const hkdf = await subtle.importKey('raw', shared, 'HKDF', false, ['deriveKey']);
    const key = await subtle.deriveKey(
        { name: 'HKDF', hash: 'SHA-256', salt: pub, info: INFO },
        hkdf,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt'],
    );
    return { pub, key };
}

function session() {
    if (!sessionPromise) {
        sessionPromise = createSession().catch((error) => {
            sessionPromise = null;
            throw error;
        });
    }
    return sessionPromise;
}

async function send(envelope) {
    const { pub, key } = await session();
    const iv = crypto.getRandomValues(new Uint8Array(IV_LEN));
    const plain = new TextEncoder().encode(JSON.stringify(envelope));
    const sealed = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, plain));

    const payload = new Uint8Array(pub.length + IV_LEN + sealed.length);
    payload.set(pub, 0);
    payload.set(iv, pub.length);
    payload.set(sealed, pub.length + IV_LEN);

    const res = await fetch(`${API_URL}/s/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: payload,
        cache: 'no-store',
    });
    if (!res.ok) {
        const error = new Error(`Server xatosi (${res.status})`);
        error.httpStatus = res.status;
        throw error;
    }
    const data = new Uint8Array(await res.arrayBuffer());
    const opened = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: data.slice(0, IV_LEN) }, key, data.slice(IV_LEN),
    );
    const { s, b } = JSON.parse(new TextDecoder().decode(opened));
    return { status: s, data: b };
}

// { method, path: '/content/version/', query, body, token } → { status, data }
// `status` — backend view'ining haqiqiy javob kodi (401, 403, 404, ...).
export async function secureRequest({ method = 'GET', path, query = {}, body = null, token = null }) {
    const envelope = { m: method, p: path, q: query, b: body, t: token };
    try {
        return await send(envelope);
    } catch (error) {
        // 400 — server konvertni ocholmadi (masalan, serverdagi SECRET_KEY
        // almashgan): yangi kalit bilan bir marta qayta urinamiz.
        if (error.httpStatus !== 400) throw error;
        sessionPromise = null;
        return send(envelope);
    }
}
