// Fetch wrapper: same origin only, JSON in/out, CSRF header on every mutating call.
let session = null;

export class ApiError extends Error {
  constructor(status, payload) {
    super(payload?.message || payload?.detail || `Erro ${status}`);
    this.status = status;
    this.payload = payload || {};
  }
}

export async function loadSession() {
  const response = await fetch("/api/session", { credentials: "same-origin" });
  session = await response.json();
  return session;
}

export function getSession() {
  return session;
}

async function request(method, path, body, { raw = false, formData = null } = {}) {
  if (!session) await loadSession();
  const headers = {};
  if (method !== "GET") headers["X-OMS-CSRF"] = session.csrf_token;
  const init = { method, headers, credentials: "same-origin" };
  if (formData) init.body = formData;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  const response = await fetch(path, init);
  if (raw) return response;
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : { message: await response.text() };
  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body = {}) => request("POST", path, body),
  put: (path, body = {}) => request("PUT", path, body),
  del: (path) => request("DELETE", path),
  async upload(path, formData, onProgress) {
    if (!session) await loadSession();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", path);
      xhr.setRequestHeader("X-OMS-CSRF", session?.csrf_token || "");
      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
      });
      xhr.addEventListener("load", () => {
        let payload = {};
        try { payload = JSON.parse(xhr.responseText || "{}"); } catch { payload = { message: xhr.responseText }; }
        if (xhr.status >= 200 && xhr.status < 300) resolve(payload);
        else reject(new ApiError(xhr.status, payload));
      });
      xhr.addEventListener("error", () => reject(new ApiError(0, { message: "Falha de rede no envio." })));
      xhr.send(formData);
    });
  },
};
