/* The backend: `window.api` is the Python bridge (bridge.js → hypr_screens/api)
 * in the app's window, mock.js in a plain browser. Every method is async and
 * rejects with an error that has {code, message}. Shapes: API.md. */

export const api = window.api;
export const BOOT = window.hyprBoot || null;

/* In the app's window (not the browser preview). */
export const inApp = () => !!BOOT;
