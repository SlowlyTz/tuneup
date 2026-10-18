/* The backend: `window.api` is the Python bridge (bridge.js → hypr_screens/api)
 * in the app's window, mock.js in a plain browser. Every method is async and
 * rejects with an error that has {code, message}. Shapes: API.md. */

export const api = window.api;
export const BOOT = window.hyprBoot || null;

/* In the app's window (not the browser preview). */
export const inApp = () => !!BOOT;

/* An API method that an older backend may not have: resolves `undefined`
 * when it is missing (the UI then leaves its part out); other errors throw. */
export async function optional(method, ...args) {
  if (typeof api[method] !== "function") return undefined;
  try {
    return await api[method](...args);
  } catch (err) {
    if (err && err.code === "unknown_method") return undefined;
    throw err;
  }
}
