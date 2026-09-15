/** Movie & TV show detail page (one module; the URL decides which). */

import {
  $, esc, renderHeader, fetchJson, formatDate, formatMoney, formatRuntime,
  scoreColor, certClass, getIso, CERT_TIP, chips, companyChips,
  openFolderPicker, flagIcon,
} from "../core.js";

let LANG = {};
let COUNTRY = {};

const parts = location.pathname.split("/").filter(Boolean);

const kind = parts[0];
const rawId = parts[1];

const mediaType = kind === "show" ? "tv" : "movie";
const mediaId = Number(rawId);
const isMovie = mediaType === "movie";

let stills = [];
let lbIndex = 0;

function factRows(facts) {
  if (!facts.length) return "";
  return `<div class="detail-grid">${facts.map(([k, v, isHtml]) =>
    `<div class="fact"><div class="fact-label">${esc(k)}</div><div class="fact-value">${
      isHtml ? v : esc(v)}</div></div>`
  ).join("")}</div>`;
}

function seasonTabs(data) {
  const seasons = data.seasons_data || [];
  if (!seasons.length) return "";
  return `<section class="detail-block"><div class="block-inner">
    <h2 class="block-title">Episodes</h2>
    <div class="season-tabs">${seasons.map((s, i) => `
      <button type="button" class="season-tab ${i === 0 ? "active" : ""}" data-season="${s.season_number}">
        Season ${s.season_number}</button>`).join("")}</div>
    ${seasons.map((s, i) => `
      <div class="episode-list" data-season-body="${s.season_number}" ${i ? "hidden" : ""}>
        ${s.episodes.map((e) => `
          <div class="episode-item">
            <div class="episode-still">${e.still ? `<img src="${esc(e.still)}" alt="" loading="lazy">` : ""}</div>
            <div class="episode-body">
              <div class="episode-name">${e.season}×${String(e.episode).padStart(2, "0")} · ${esc(e.name)}</div>
              <div class="episode-meta">${esc(formatDate(e.air_date) || "")}${e.runtime ? ` · ${esc(formatRuntime(e.runtime))}` : ""}</div>
              ${e.overview ? `<div class="episode-overview">${esc(e.overview)}</div>` : ""}
            </div>
          </div>`).join("")}
      </div>`).join("")}
  </div></section>`;
}

function stillsBlock() {
  if (!stills.length) return "";
  return `<section class="detail-block"><div class="block-inner"><h2 class="block-title">Stills</h2>
    <div class="gallery-wrap">
      <button type="button" class="carousel-btn" id="stillPrev">‹</button>
      <div class="gallery-strip" id="stillStrip">${stills.map((s, i) =>
        `<button type="button" class="still-thumb" data-i="${i}"><img src="${esc(s.thumb)}" alt="" loading="lazy"></button>`
      ).join("")}</div>
      <button type="button" class="carousel-btn" id="stillNext">›</button>
    </div></div></section>`;
}

async function loadCollection(m) {
  if (!m.collection?.id) return;
  try {
    const data = await fetchJson(`/api/collection/${m.collection.id}?limit=100`);
    const items = data.items || [];
    if (!items.length) return;
    $("sectionCollection").hidden = false;
    $("collectionTitle").textContent = data.collection?.name || "Collection";
    $("collectionRow").innerHTML = items.map((item) => `
      <a class="collection-card${item.id === m.id ? " is-current" : ""}" href="/${item.media_type === "tv" ? "show" : "movie"}/${item.id}">
        <div class="collection-poster">${item.poster
          ? `<img src="${esc(item.poster)}" alt="" loading="lazy">`
          : `<div class="poster-placeholder">${esc(item.title)}</div>`}</div>
        <div class="collection-name">${esc(item.title)}</div>
        ${item.year ? `<div class="collection-year">${item.year}</div>` : ""}
      </a>`).join("");
  } catch (e) {
    console.error(e);
  }
}

function bindAddButton(m) {
  const button = $("btnAddLib");
  const sync = (added) => {
    button.textContent = added ? "In library" : "+ Add to library";
    button.classList.toggle("is-added", added);
  };
  if (m.in_library) sync(true);
  button.addEventListener("click", async () => {
    const result = await openFolderPicker(mediaType, m.id);
    if (result) sync((result.folder_ids || []).length > 0);
  });
}

/* ------------------------------------------------------------- lightbox */

function openLb(i) {
  lbIndex = i;
  $("lbImg").src = stills[lbIndex].full;
  $("lightbox").hidden = false;
}
function closeLb() {
  $("lightbox").hidden = true;
}
function lbNav(d) {
  lbIndex = (lbIndex + d + stills.length) % stills.length;
  $("lbImg").src = stills[lbIndex].full;
}

function bindLightbox() {
  $("lbClose").onclick = closeLb;
  $("lbPrev").onclick = () => lbNav(-1);
  $("lbNext").onclick = () => lbNav(1);
  $("lightbox").addEventListener("click", (e) => { if (e.target.id === "lightbox") closeLb(); });
  document.addEventListener("keydown", (e) => {
    if ($("lightbox").hidden) return;
    if (e.key === "Escape") closeLb();
    if (e.key === "ArrowLeft") lbNav(-1);
    if (e.key === "ArrowRight") lbNav(1);
  });
  document.addEventListener("click", (e) => {
    const t = e.target.closest(".still-thumb");
    if (t) openLb(+t.dataset.i);
  });
  $("stillPrev").onclick = () => $("stillStrip").scrollBy({ left: -$("stillStrip").clientWidth * 0.85, behavior: "smooth" });
  $("stillNext").onclick = () => $("stillStrip").scrollBy({ left: $("stillStrip").clientWidth * 0.85, behavior: "smooth" });
}

/* ---------------------------------------------------------------- render */

async function render(m) {
  document.title = `${m.title} – Catalog`;
  $("detailLoading").hidden = true;
  const root = $("detailRoot");
  root.hidden = false;

  const side = [
    `<div class="detail-add"><button type="button" id="btnAddLib">+ Add to library</button></div>`,
  ];
  const links = [
    `<a class="ext-link-sm" href="https://www.themoviedb.org/${mediaType}/${m.id}" target="_blank" rel="noopener">TMDB</a>`,
  ];
  if (m.imdb_id) links.push(`<a class="ext-link-sm" href="https://www.imdb.com/title/${esc(m.imdb_id)}/" target="_blank" rel="noopener">IMDb</a>`);
  if (m.homepage) links.push(`<a class="ext-link-sm web-link" href="${esc(m.homepage)}" target="_blank" rel="noopener" title="Website">WEBSITE</a>`);
  side.push(`<div class="side-links">${links.join("")}</div>`);

  const meta = [];
  if (m.certification) meta.push(`<span class="meta-pill ${certClass(m.certification)}" title="${esc(CERT_TIP[m.certification] || "")}">${esc(m.certification)}</span>`);
  if (m.year) meta.push(`<span>${esc(String(m.year))}</span>`);
  const rt = isMovie ? formatRuntime(m.runtime) : (m.episodes ? `${m.episodes} episodes` : "");
  if (rt) meta.push(`<span>${esc(rt)}</span>`);
  if (m.vote_average > 0) meta.push(`<span class="meta-score" style="color:${scoreColor(m.vote_average)}" title="${(m.vote_count || 0).toLocaleString()} votes">★ ${m.vote_average}</span>`);

  const oc = (m.origin_country || []).map((c) => {
    const name = COUNTRY[c]?.name || c;
    const official = COUNTRY[c]?.official;
    return `${flagIcon(c)}<span${official && official !== name ? ` title="${esc(official)}"` : ""}>${esc(name)}</span>`;
  }).join(", ");
  const facts = [];
  const push = (k, v, isHtml = false) => { if (v) facts.push([k, v, isHtml]); };
  if (isMovie) {
    push("Type", m.type);
    push("Status", m.status);
    push("Origin country", oc, true);
    push("Budget", formatMoney(m.budget));
    push("Revenue", formatMoney(m.revenue));
    push("Collection", m.collection?.name);
    push("Release date", formatDate(m.release_date));
  } else {
    push("Type", m.type);
    push("Status", m.status);
    push("Origin country", oc, true);
    push("Seasons", m.seasons);
    push("Episodes", m.episodes);
    push("First aired", formatDate(m.first_air_date));
    push("Last aired", formatDate(m.last_air_date));
    push("Networks", (m.networks || []).map((n) => n.name).join(", "));
  }
  push("Original language", LANG[m.original_language] || (m.original_language || "").toUpperCase());
  push("Popularity", m.popularity && String(m.popularity));
  push("Votes", m.vote_count && m.vote_count.toLocaleString());

  const spoken = (m.spoken_languages || []).map((l) => l.english_name || l.name).filter(Boolean);
  const langs = (m.languages || []).map((c) => LANG[c] || c).filter(Boolean);
  stills = m.stills || [];

  root.innerHTML = `
    <div class="detail-backdrop" id="detailBackdrop"></div>
    <div class="detail-container">
      <div class="detail-poster-col">
        <div class="detail-poster">${m.poster ? `<img src="${esc(m.poster)}" alt="" fetchpriority="high">` : `<div class="poster-placeholder">${esc(m.title)}</div>`}</div>
        <div class="poster-side">${side.join("")}</div>
      </div>
      <div class="detail-info">
        <h1 class="detail-title">${esc(m.title)}</h1>
        ${m.original_title && m.original_title !== m.title ? `<p class="detail-original">${esc(m.original_title)}</p>` : ""}
        ${m.tagline ? `<p class="detail-tagline">“${esc(m.tagline)}”</p>` : ""}
        <div class="detail-meta">${meta.join("")}</div>
        <div class="detail-genres">${(m.genres || []).map((g) => `<span class="genre-chip">${esc(g)}</span>`).join("")}</div>
        ${m.overview ? `<p class="detail-overview">${esc(m.overview)}</p>` : ""}
        ${factRows(facts)}
      </div>
    </div>
    ${stillsBlock()}
    ${isMovie ? "" : seasonTabs(m)}
    <section class="detail-block"><div class="block-inner">
    ${companyChips(m.production_companies)}
    ${chips("Spoken languages", spoken)}
    ${chips("Languages", langs)}
    ${chips("Keywords", m.keywords || [])}
  </div></section>
    <section class="detail-block" id="sectionCollection" hidden><div class="block-inner">
      <h2 class="block-title" id="collectionTitle">Collection</h2>
      <div class="collection-row" id="collectionRow"></div>
    </div></section>`;

  if (m.backdrop) $("detailBackdrop").style.backgroundImage = `url("${esc(m.backdrop)}")`;
  bindAddButton(m);
  if (stills.length) bindLightbox();
  loadCollection(m);
}

async function load() {
  try {
    ({ languages: LANG, countries: COUNTRY } = await getIso());
    const data = await fetchJson(`/api/${kind}/${mediaId}`);
    render(data);
  } catch (e) {
    console.error(e);
    $("detailLoading").hidden = true;
    $("detailError").hidden = false;
  }
}

renderHeader();
load();
