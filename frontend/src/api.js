// API 封装：同源相对路径，JWT 自动携带
const TOKEN_KEY = 'jubensha_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {};
  const t = getToken();
  if (t) headers['Authorization'] = `Bearer ${t}`;
  let payload;
  if (form) {
    payload = form; // FormData / URLSearchParams：fetch 自动设 Content-Type
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  const res = await fetch('/api/v1' + path, { method, headers, body: payload });
  if (res.status === 401) {
    setToken(null);
    if (!location.pathname.startsWith('/login')) location.href = '/login';
    throw new Error('登录已过期，请重新登录');
  }
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && data.detail) || `请求失败(${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

// 二进制下载（带 token）：语音播放用 fetch→blob→objectURL
export async function apiBlob(path) {
  const headers = {};
  const t = getToken();
  if (t) headers['Authorization'] = `Bearer ${t}`;
  const res = await fetch('/api/v1' + path, { headers });
  if (!res.ok) throw new Error(`下载失败(${res.status})`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
