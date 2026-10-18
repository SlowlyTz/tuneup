/* The little desktop that shows a window look (gaps, corners, border, opacity, blur). */
import { esc } from "../../core/dom.js";
import { t } from "../../core/i18n.js";
import { S } from "../../core/state.js";

/* The look's values as CSS variables of the preview. */
export function lpVars(v) {
  const seeThrough = v.activeOpacity < 1 || v.inactiveOpacity < 1 || (v.apps || []).length;
  const blur = v.blur && seeThrough ? v.blurSize * 0.8 : 0;
  const theme = (S.look && S.look.themeBorder && S.look.themeBorder.colors) || [];
  const [c1, c2] = v.borderColors || [theme[0] || "var(--c-accent)", theme[1] || theme[0] || "var(--c-accent)"];
  return `--gi:${v.gapsIn};--go:${v.gapsOut};--rd:${v.rounding};--bw:${v.border};--tr:${Math.round((1 - v.inactiveOpacity) * 100)};--tr-act:${Math.round((1 - v.activeOpacity) * 100)};--bl:${blur};--bc1:${c1};--bc2:${c2};--ba:${v.borderColors ? v.borderAngle : 0};--bc-in:var(--c-selection)`;
}

export function lookPreview(v, mini = false) {
  const term = `<div class="term"><div><span class="p">~/dev</span> <span class="d">❯</span> hypr-screens status</div><div><span class="g">●</span> ${esc(t("Laptop"))} <span class="d">· ${esc(t("fixed"))}</span></div><div><span class="g">●</span> HP 32f <span class="d">· ${esc(t("Desktops 1–10"))}</span></div><div><span class="p">~/dev</span> <span class="d">❯</span> <span class="y">▍</span></div></div>`;
  const doc = '<div class="doc"><i class="h"></i><i></i><i style="width:85%"></i><i style="width:70%"></i><i class="acc"></i><i style="width:90%"></i></div>';
  const media = '<div class="media"><span class="art"></span><span class="lines"><i></i><i style="width:45%"></i><i style="width:100%;height:3px;margin-top:4px"></i></span></div>';
  return `<div class="lp${mini ? " mini" : ""}" style="${lpVars(v)}" aria-hidden="true"><div class="lp-bar"><i class="on"></i><i></i><i></i><i></i><span>14:32</span></div><div class="lp-area"><div class="lp-win a active">${term}</div><div class="lp-win">${doc}</div><div class="lp-win">${media}</div></div></div>`;
}
