const BASE_URL = ''; // yoki backend URL, hozir nisbiy yo'llar backendga proxy qilinadi

export async function fetchJSON(url) {
  const res = await fetch(BASE_URL + url);
  if (!res.ok) throw new Error(`Fetch error: ${res.statusText}`);
  return res.json();
}

export async function postJSON(url, data) {
  const res = await fetch(BASE_URL + url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`POST error: ${res.statusText}`);
  return res.json();
}

export async function patchJSON(url, data) {
  const res = await fetch(BASE_URL + url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`PATCH error: ${res.statusText}`);
  return res.json();
}

export async function deleteResource(url) {
  const res = await fetch(BASE_URL + url, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`DELETE error: ${res.statusText}`);
  // DELETE might not return JSON, so return empty object or parse if content-type is json
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.indexOf("application/json") !== -1) {
    return res.json();
  } else {
    return {};
  }
}

export async function uploadFile(url, file, fieldName = 'file') {
  const formData = new FormData();
  formData.append(fieldName, file);

  const res = await fetch(BASE_URL + url, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload error: ${res.statusText}`);
  return res.json();
}
