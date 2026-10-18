/* The pages of the app and the hash route (#/page/sub). */
import { t } from "./i18n.js";
import { S } from "./state.js";
import { render } from "./view.js";

/* needs: the state parts the page shows; when: shown only if it returns true. */
const PAGES = [
  { id: "home", label: () => t("Home"), icon: "home", needs: ["screens", "sound", "samsung", "widgets"], core: ["screens"] },
  { id: "screens", label: () => t("Screens"), icon: "monitor", needs: ["screens", "keys"] },
  { id: "keys", label: () => t("Keyboard"), icon: "keyboard", needs: ["keys"] },
  { id: "look", label: () => t("Windows"), icon: "window", needs: ["look"] },
  { id: "widgets", label: () => t("Widgets"), icon: "widgets", needs: ["widgets", "screens"], core: ["widgets"] },
  { id: "sound", label: () => t("Sound"), icon: "speaker", needs: ["sound"] },
  { id: "camera", label: () => t("Camera"), icon: "camera", needs: ["camera"] },
  { id: "power", label: () => t("Battery & power"), icon: "battery", needs: ["samsung"], when: () => S.samsung && S.samsung.available },
  { id: "general", label: () => t("General"), icon: "sliders", needs: ["general"] },
];
export const pageOf = (id) => PAGES.find((p) => p.id === id);
export const shownPages = () => PAGES.filter((p) => !p.when || p.when());

export function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const page = pageOf(parts[0]) ? parts[0] : "home";
  return { page, sub: parts[1] || null };
}

/* Opens `hash` (or renders again when it is open already). */
export const go = (hash) => { if (location.hash !== hash) location.hash = hash; else render(true); };
