/** Shared frontend core: escaping, fetch, labels, formatters, theme, header, modals. */

/* -------------------------------------------------------------- utilities */

export function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function $(id) {
  return document.getElementById(id);
}

export async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || `Request failed: ${response.status}`);
  }
  return data;
}

/* ---------------------------------------------------------------- labels */

let isoPromise = null;

/** ISO 3166-1 / ISO 639-1 code -> name maps from /api/iso (cached). */
export function getIso() {
  isoPromise ??= fetchJson("/api/iso").catch(() => ({ countries: {}, languages: {} }));
  return isoPromise;
}

export const CERT_TIP = {
  G: "General audiences", PG: "Parental guidance suggested",
  "PG-13": "Parents strongly cautioned (under 13)", R: "Restricted (under 17 with adult)",
  "NC-17": "Adults only", NR: "Not rated",
  "TV-Y": "All children", "TV-G": "General audience", "TV-PG": "Parental guidance",
  "TV-14": "Parents cautioned (14+)", "TV-MA": "Mature audience (17+)",
};

/* ------------------------------------------------------------ formatters */

export function scoreColor(v) {
  const t = Math.max(0, Math.min(10, Number(v) || 0)) / 10;
  let r, g, b;
  if (t < 0.5) {
    const u = t * 2;
    r = Math.round(180 + 40 * u); g = Math.round(30 + 150 * u); b = 20;
  } else {
    const u = (t - 0.5) * 2;
    r = Math.round(220 - 190 * u); g = Math.round(180 - 20 * u); b = Math.round(20 + 40 * u);
  }
  return `rgb(${r},${g},${b})`;
}

export function certClass(cert) {
  if (!cert) return "";
  const u = cert.toUpperCase();
  if (["G", "TV-Y", "TV-G"].includes(u)) return "cert-g";
  if (["PG", "TV-PG", "TV-Y7"].includes(u)) return "cert-pg";
  if (["PG-13", "TV-14"].includes(u)) return "cert-pg13";
  if (["R", "TV-MA"].includes(u)) return "cert-r";
  if (u === "NC-17") return "cert-nc17";
  return "";
}

export function formatRuntime(mins) {
  if (!mins || mins <= 0) return "";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h && m) return `${h}h ${m}m`;
  return h ? `${h}h` : `${m}m`;
}

export function formatDate(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T00:00:00");
  return isNaN(d) ? iso : d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

export function formatMoney(n) {
  if (!n) return null;
  return "$" + Number(n).toLocaleString("en-US");
}

/** Tiny country flag; a styled stub replaces it when the svg file is missing. */
export function flagIcon(code) {
  return `<img class="flag-ico" src="/static/assets/flags/4x3/${esc(String(code).toLowerCase())}.svg" alt=""
    loading="lazy" onerror="this.classList.add('is-missing');this.removeAttribute('src')">`;
}

/* ---------------------------------------------------------------- header */

const SUN_SVG = `<svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`;
const MOON_SVG = `<svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a7 7 0 0 0 11.5 11.5z"/></svg>`;

/** Render the site header (logo, optional nav tabs, auth area, theme toggle). */
export function renderHeader({ nav = "" } = {}) {
  const header = document.querySelector(".header");
  if (!header) return;
  header.innerHTML = `
    <div class="header-inner">
      <a href="/" class="logo">Catalog</a>
      <nav class="nav">${nav}</nav>
      <div class="header-right">
        <div class="auth-area" id="authArea"></div>
        <button class="language-btn" type="button" title="English">EN</button>
        <button class="theme-btn" id="themeToggle" title="Toggle theme" aria-label="Toggle theme">
          ${SUN_SVG}${MOON_SVG}
        </button>
      </div>
    </div>`;
  $("themeToggle").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.getAttribute("data-theme") !== "dark";
    if (dark) root.setAttribute("data-theme", "dark");
    else root.removeAttribute("data-theme");
    localStorage.setItem("theme", dark ? "dark" : "light");
  });
  renderAuthHeader($("authArea"));
}

/* ------------------------------------------------------------------ auth */

export async function getMe() {
  const response = await fetch("/api/me");
  return response.json();
}

async function renderAuthHeader(container) {
  if (!container) return;
  const me = await getMe().catch(() => ({ authenticated: false }));
  if (!me.authenticated) {
    container.innerHTML = `<a class="auth-link auth-btn" href="/login">Login</a>`;
    return;
  }
  container.innerHTML = `
    <a class="auth-link auth-btn" href="/library">Library</a>
    <div class="profile-wrap">
      <button type="button" class="profile-btn" id="profileBtn">${esc(me.user.username)}</button>
      <div class="profile-menu" id="profileMenu" hidden>
        <a href="/library">Library</a>
        <button type="button" id="logoutBtn">Log out</button>
      </div>
    </div>`;
  const btn = $("profileBtn");
  const menu = $("profileMenu");
  btn?.addEventListener("click", (e) => { e.stopPropagation(); menu.hidden = !menu.hidden; });
  document.addEventListener("click", () => { if (menu) menu.hidden = true; });
  $("logoutBtn")?.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    location.href = "/login";
  });
}

/* ---------------------------------------------------------------- modals */

/** Show a modal; `body` is the inner HTML. Clicks on [data-act] resolve({act, el}). */
export function openModal(body) {
  const back = document.createElement("div");
  back.className = "modal-back";
  back.innerHTML = `<div class="modal">${body}</div>`;
  document.body.appendChild(back);
  return new Promise((resolve) => {
    back.addEventListener("click", (e) => {
      if (e.target === back) { back.remove(); resolve({ act: "cancel" }); return; }
      const btn = e.target.closest("[data-act]");
      if (btn) {
        back.remove();
        resolve({ act: btn.dataset.act, el: back });
      }
    });
  });
}

/** Folder picker for one media item; resolves to the sync response or null. */
export async function openFolderPicker(mediaType, mediaId) {
  const me = await getMe().catch(() => ({ authenticated: false }));
  if (!me.authenticated) {
    location.href = "/login";
    return null;
  }
  let folders = [];
  let selected = new Set();
  try {
    const [foldersRes, memRes] = await Promise.all([
      fetchJson("/api/library/folders"),
      fetchJson(`/api/library/membership?media_type=${mediaType}&media_id=${mediaId}`),
    ]);
    folders = foldersRes.folders || [];
    selected = new Set(memRes.folder_ids || []);
  } catch {
    location.href = "/login";
    return null;
  }
  const list = folders.map((f) => `
    <label class="folder-option">
      <input type="checkbox" value="${f.id}" ${selected.has(f.id) ? "checked" : ""}>
      <span class="folder-option-name">${esc(f.name)}</span>
      <span class="folder-option-count">${f.item_count}</span>
    </label>`).join("");

  const { act, el } = await openModal(`
    <h3>Add to folders</h3>
    <p class="modal-hint">Select one or more lists</p>
    <div class="folder-list">${list || '<p class="modal-empty">No folders yet</p>'}</div>
    <div class="modal-actions">
      <button type="button" class="btn-ghost" data-act="cancel">Cancel</button>
      <button type="button" class="btn-solid" data-act="ok">Save</button>
    </div>`);

  if (act === "cancel") return null;
  if (act === "ok") {
    const ids = [...el.querySelectorAll('.folder-option input[type="checkbox"]:checked')]
      .map((input) => Number(input.value));
    return fetchJson("/api/library/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_type: mediaType, media_id: mediaId, folder_ids: ids }),
    });
  }
  return null;
}

export async function promptFolderName(title = "New folder") {
  const { act, el } = await openModal(`
    <h3>${esc(title)}</h3>
    <input class="modal-input" id="folderNameInput" placeholder="Folder name" maxlength="64" autocomplete="off">
    <div class="modal-actions">
      <button type="button" class="btn-ghost" data-act="cancel">Cancel</button>
      <button type="button" class="btn-solid" data-act="ok">Create</button>
    </div>`);
  if (act !== "ok") return null;
  return el.querySelector("#folderNameInput").value.trim() || null;
}

/* ------------------------------------------------------- person snippets */

export const SILHOUETTE = `<svg viewBox="0 0 64 96" width="40" height="56" xmlns="http://www.w3.org/2000/svg"><circle cx="32" cy="22" r="14" fill="currentColor" opacity=".35"/><path d="M8 90c0-16 10.7-28 24-28s24 12 24 28" fill="currentColor" opacity=".35"/></svg>`;

export function personCard(p, sub) {
  const photo = p.profile ? `<img src="${esc(p.profile)}" alt="" loading="lazy">` : SILHOUETTE;
  return `<a class="person-sm" href="/person/${p.id}"><div class="person-sm-photo">${photo}</div>
    <div class="person-sm-name" title="${esc(p.name)}">${esc(p.name || "")}</div>
    ${sub ? `<div class="person-sm-sub" title="${esc(sub)}">${esc(sub)}</div>` : ""}</a>`;
}

export function chips(title, items) {
  if (!items?.length) return "";
  return `<div class="extra-block"><h3>${esc(title)}</h3><div class="chip-list">
    ${items.map((i) => `<span class="chip">${esc(i)}</span>`).join("")}</div></div>`;
}

export function companyChips(items) {
  if (!items?.length) return "";
  return `<div class="extra-block"><h3>Production companies</h3><div class="chip-list">
    ${items.map((c) => `<a class="chip" href="/company/${c.id}">${esc(c.name || "")}</a>`).join("")}
  </div></div>`;
}
