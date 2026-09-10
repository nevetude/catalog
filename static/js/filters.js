/** Unified filter sidebar shared by every listing page (index, library, company, collection). */

import { $, esc, flagIcon, getIso } from "./core.js";

/* --------------------------------------------------- predefined chip order */

/** Checkbox lists in display order; values missing from the current dataset are hidden. */
const TYPE_MOVIE = ["Movie", "Short", "TV Movie", "Collection", "First in collection"];
const TYPE_TV = ["Scripted", "Reality", "Documentary", "News", "Talk", "Variety"];
const GENRES_MOVIE = [
  "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family",
  "Fantasy", "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction",
  "TV Movie", "Thriller", "War", "Western",
];
const GENRES_TV = [
  "Action & Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family",
  "Kids", "Mystery", "News", "Reality", "Sci-Fi & Fantasy", "Soap", "Talk", "War & Politics",
];
const CERT_MOVIE = ["G", "PG", "PG-13", "R", "NC-17", "NR"];
const CERT_TV = ["TV-Y", "TV-Y7", "TV-Y7-FV", "TV-G", "TV-PG", "TV-14", "TV-MA"];
const STATUS_TV = [
  { value: "Returning Series", label: "Ongoing" },
  { value: "Ended", label: "Finished" },
  { value: "Canceled", label: "Canceled" },
  { value: "In Production", label: "In production" },
];
const STATUS_MOVIE = [
  { value: "Released", label: "Released" },
  { value: "Post Production", label: "Post production" },
  { value: "In Production", label: "In production" },
  { value: "Planned", label: "Planned" },
  { value: "Rumored", label: "Rumored" },
  { value: "Canceled", label: "Canceled" },
];
const CONTENT = [
  ["short", "Short"], ["anime", "Anime"], ["donghua", "Donghua"],
  ["aeni", "Aeni"], ["amerime", "Amerime"], ["tv_movie", "TV Movie"],
];
const NSFW = [
  ["adult", "Adult"], ["softcore", "Softcore"], ["gay", "Gay"], ["lesbian", "Lesbian"],
];

const FLAGS_SIDEBAR_HTML = `
  <div class="filter-section">
    <div class="filter-header">Content</div>
    <div class="check-list cols-2" id="contentChips"></div>
  </div>

  <div class="filter-section">
    <div class="filter-header">NSFW</div>
    <div class="check-list cols-2" id="nsfwChips"></div>
  </div>
`;

const SIDEBAR_HTML = `
  <div class="filter-section" data-kind="type">
    <div class="filter-header">Type</div>
    <select class="filter-select" data-role="type-select">
      <option value="all" selected>All</option>
      <option value="movie">Movies</option>
      <option value="tv">TV Shows</option>
    </select>
  </div>

  <div class="filter-section">
    <div class="filter-header">Year</div>
    <div class="range-inputs">
      <input type="number" id="yearFrom"><span>—</span><input type="number" id="yearTo">
    </div>
    <div class="dual-range" id="yearRange">
      <input type="range" id="yearFromR" min="1900" max="2030" value="1900">
      <input type="range" id="yearToR" min="1900" max="2030" value="2030">
    </div>
  </div>

  <div class="filter-section movie-only">
    <div class="filter-header">Runtime (min)</div>
    <div class="range-inputs">
      <input type="number" id="rtFrom"><span>—</span><input type="number" id="rtTo">
    </div>
    <div class="dual-range" id="rtRange">
      <input type="range" id="rtFromR" min="0" max="300" value="0">
      <input type="range" id="rtToR" min="0" max="300" value="300">
    </div>
  </div>

  <div class="filter-section tv-only" style="display:none">
    <div class="filter-header">Episodes</div>
    <div class="range-inputs">
      <input type="number" id="epFrom"><span>—</span><input type="number" id="epTo">
    </div>
  </div>

  <div class="filter-section movie-only">
    <div class="filter-header">Budget (USD)</div>
    <div class="range-inputs">
      <input type="number" id="budgetFrom"><span>—</span><input type="number" id="budgetTo">
    </div>
    <div class="dual-range" id="budgetRange">
      <input type="range" id="budgetFromR" min="0" max="500000000" value="0" step="1">
      <input type="range" id="budgetToR" min="0" max="500000000" value="500000000" step="1">
    </div>
  </div>

  <div class="filter-section">
    <div class="filter-header">Score</div>
    <div class="range-inputs">
      <input type="number" id="minScore" step="0.1" min="0" max="10" placeholder="0"><span>—</span>
      <input type="number" id="maxScore" step="0.1" min="0" max="10" placeholder="10">
    </div>
    <div class="dual-range" id="scoreRange">
      <input type="range" id="minScoreR" min="0" max="10" step="0.1" value="0">
      <input type="range" id="maxScoreR" min="0" max="10" step="0.1" value="10">
    </div>
  </div>

  <div class="filter-section">
    <div class="filter-header">Min votes</div>
    <input type="number" class="full-input" id="minVotes" min="0" placeholder="0">
  </div>

  <div class="filter-section" data-facet="type">
    <div class="filter-header">Type</div>
    <div class="check-list cols-2" id="typeChips"></div>
  </div>

  <div class="filter-section" data-facet="genre">
    <div class="filter-header">Genres</div>
    <div class="check-list cols-2" id="genreChips"></div>
  </div>

  ${FLAGS_SIDEBAR_HTML}

  <div class="filter-section" data-section="company">
    <div class="filter-header country-header" data-accordion-header>
      <span>Studios</span>
      <button type="button" class="accordion-toggle" aria-label="Toggle studios list">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
      </button>
    </div>
    <div class="acc-body open" data-acc-pinned><div class="acc-inner">
      <div class="check-list cols-2" id="companyChips"></div>
    </div></div>
    <div class="acc-body" data-acc-full><div class="acc-inner">
      <div class="check-list cols-2" id="companyMore"></div>
    </div></div>
  </div>

  <div class="filter-section tv-only" style="display:none" data-section="network">
    <div class="filter-header country-header" data-accordion-header>
      <span>Networks</span>
      <button type="button" class="accordion-toggle" aria-label="Toggle networks list">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
      </button>
    </div>
    <div class="acc-body open" data-acc-pinned><div class="acc-inner">
      <div class="check-list cols-2" id="networkChips"></div>
    </div></div>
    <div class="acc-body" data-acc-full><div class="acc-inner">
      <div class="check-list cols-2" id="networkMore"></div>
    </div></div>
  </div>

  <div class="filter-section" data-facet="cert">
    <div class="filter-header" id="certLabel">MPA</div>
    <div class="check-list cols-2" id="certChips"></div>
  </div>

  <div class="filter-section country-block" data-section="country">
    <div class="filter-header country-header" data-accordion-header>
      <span>Country</span>
      <button type="button" class="accordion-toggle" aria-label="Toggle country list">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
      </button>
    </div>
    <div class="acc-body open" data-acc-pinned><div class="acc-inner">
      <div class="check-list cols-2" id="countryChips"></div>
    </div></div>
    <div class="acc-body" data-acc-full><div class="acc-inner">
      <div class="check-list cols-2" id="countryMore"></div>
    </div></div>
  </div>

  <div class="filter-section" data-facet="lang">
    <div class="filter-header">Language</div>
    <div class="check-list cols-2" id="langChips"></div>
  </div>

  <div class="filter-section" data-facet="status">
    <div class="filter-header sm">Status</div>
    <div class="check-list cols-2" id="statusFilters"></div>
  </div>
`;

const RANGES = [
  { wrap: "yearRange", from: "yearFromR", to: "yearToR", numFrom: "yearFrom", numTo: "yearTo" },
  { wrap: "rtRange", from: "rtFromR", to: "rtToR", numFrom: "rtFrom", numTo: "rtTo" },
  { wrap: "budgetRange", from: "budgetFromR", to: "budgetToR", numFrom: "budgetFrom", numTo: "budgetTo" },
  { wrap: "scoreRange", from: "minScoreR", to: "maxScoreR", numFrom: "minScore", numTo: "maxScore" },
];

/** Countries always visible under the header, in this row-major 2-column order. */
const PINNED_COUNTRIES = ["US", "GB", "FR", "DE", "JP", "KR", "RU", "SU"];

/** Top studios/networks pinned in the accordion (TMDB ids), most titles first. */
const PINNED_COMPANIES = ["174", "33", "4", "2", "5", "25", "521", "420"];
const PINNED_NETWORKS = ["213", "49", "4", "174", "6", "19", "2", "16"];

/** Accordion collapses to a flat list when the full list is this short. */
const FLAT_LIMIT = 12;

/* ------------------------------------------------------------------ helpers */

let bounds = { year_min: 1900, year_max: 2030, runtime_min: 0, runtime_max: 300, budget_min: 0, budget_max: 500000000 };
let checkboxState = {};
let optionsCache = {};
/** Tri-state chips: null (off) -> "yes" (checked) -> "no" (minus) -> null. */
const TRI_STATE_PARAMS = {
  Collection: "collection",
  "First in collection": "first_in_collection",
};
let triState = { Collection: null, "First in collection": null };

function paintDual(wrap, fromEl, toEl) {
  const min = Number(fromEl.min);
  const max = Number(fromEl.max);
  if (max <= min) return;
  const a = Number(fromEl.value);
  const b = Number(toEl.value);
  const left = ((Math.min(a, b) - min) / (max - min)) * 100;
  const right = ((Math.max(a, b) - min) / (max - min)) * 100;
  wrap.style.setProperty("--range-left", `${left}%`);
  wrap.style.setProperty("--range-right", `${right}%`);
}

function bindDual({ wrap, from, to, numFrom, numTo }) {
  const wf = $(wrap);
  const rf = $(from);
  const rt = $(to);
  const nf = $(numFrom);
  const nt = $(numTo);
  if (!wf || !rf || !rt || !nf || !nt) return;

  const syncFromRange = () => {
    let a = Number(rf.value);
    let b = Number(rt.value);
    if (a > b) [a, b] = [b, a];
    nf.value = a;
    nt.value = b;
    paintDual(wf, rf, rt);
  };
  const syncFromNumber = () => {
    const min = Number(rf.min);
    const max = Number(rf.max);
    let a = nf.value === "" ? min : Number(nf.value);
    let b = nt.value === "" ? max : Number(nt.value);
    a = Math.max(min, Math.min(max, Number.isFinite(a) ? a : min));
    b = Math.max(min, Math.min(max, Number.isFinite(b) ? b : max));
    if (a > b) [a, b] = [b, a];
    rf.value = a;
    rt.value = b;
    if (nf.value !== "") nf.value = a;
    if (nt.value !== "") nt.value = b;
    paintDual(wf, rf, rt);
  };
  rf.addEventListener("input", syncFromRange);
  rt.addEventListener("input", syncFromRange);
  nf.addEventListener("change", syncFromNumber);
  nt.addEventListener("change", syncFromNumber);
  paintDual(wf, rf, rt);
}

function renderChecks(container, values, labels, group, titles = {}, icons = false,
                      keepOrder = false, prechecked = null) {
  if (!container) return;
  const sorted = keepOrder ? values : [...values].sort((a, b) =>
    String(labels[a] ?? a).toLowerCase().localeCompare(String(labels[b] ?? b).toLowerCase()));
  const idBase = `f-${group}-${container.id}`;
  container.innerHTML = sorted.map((value, i) => {
    const state = checkboxState[group];
    const checked = state && value in state ? !!state[value]
      : !!(prechecked && prechecked.has(value));
    return `
    <label class="check-item" for="${idBase}-${i}" title="${esc(titles[value] ?? "")}">
      ${icons ? (typeof icons === "function" ? icons(value) : flagIcon(value)) : ""}
      <input type="checkbox" id="${idBase}-${i}" data-filter-group="${esc(group)}"
             data-filter-value="${esc(value)}" ${checked ? "checked" : ""}>
      <span>${esc(labels[value] ?? value)}</span>
    </label>`;
  }).join("");
  if (group === "type") {
    for (const value of Object.keys(TRI_STATE_PARAMS)) {
      const chip = container.querySelector(`input[data-filter-value="${value}"]`);
      if (chip) {
        chip.checked = triState[value] === "yes";
        chip.indeterminate = triState[value] === "no";
      }
    }
  }
}

/** Content/NSFW chips: predefined order, only flags present in the dataset. */
function renderFlagChips(container, pairs, counts) {
  if (!container) return;
  const section = container.closest(".filter-section");
  if (!section) return;
  const rows = pairs.filter(([flag]) => (counts?.[flag] ?? 0) > 0);
  section.style.display = rows.length ? "" : "none";
  container.innerHTML = rows.map(([flag, label], i) => `
    <label class="check-item" for="flag-${flag}">
      <input type="checkbox" id="flag-${flag}" data-feature="${esc(flag)}">
      <span>${esc(label)}</span>
    </label>`).join("");
}

function renderOrderedChips(container, order, available, group) {
  if (!container) return;
  const section = container.closest(".filter-section");
  if (!section) return;
  const values = order.filter((v) => available.has(v));
  section.style.display = values.length ? "" : "none";
  renderChecks(container, values, {}, group);
}

function renderStatusChips(container, mode, available, prechecked) {
  if (!container) return;
  const section = container.closest(".filter-section");
  if (!section) return;
  const base = mode === "movie" ? STATUS_MOVIE : mode === "tv" ? STATUS_TV : [...STATUS_MOVIE, ...STATUS_TV];
  const list = base.filter((s) => available.has(s.value));
  section.style.display = list.length ? "" : "none";
  container.innerHTML = list.map((item, i) => `
    <label class="check-item" for="status-${i}">
      <input type="checkbox" id="status-${i}" data-status="${esc(item.value)}"
             ${prechecked?.has(item.value) ? "checked" : ""}>
      <span>${esc(item.label)}</span>
    </label>`).join("");
}

/** Company/network logo over the checkbox; a stub when TMDB has no logo file. */
function logoIcon(entity) {
  if (entity?.logo) {
    return `<img class="logo-ico" src="https://image.tmdb.org/t/p/w45${esc(entity.logo)}"
      alt="" loading="lazy" onerror="this.classList.add('is-missing');this.removeAttribute('src')">`;
  }
  return `<span class="logo-ico is-missing"></span>`;
}

/** Pinned-top accordion of entities with logos; flat list when short. */
function renderEntityAccordion(section, pinnedEl, fullEl, items, pinnedIds, group) {
  if (!pinnedEl || !fullEl) return;
  const byId = new Map((items || []).map((c) => [String(c.id), c]));
  if (!byId.size) {
    if (section) section.style.display = "none";
    return;
  }
  if (section) section.style.display = "";
  const labels = Object.fromEntries([...byId].map(([id, c]) => [id, c.name]));
  const icon = (id) => logoIcon(byId.get(id));
  const flat = byId.size <= FLAT_LIMIT;
  section?.classList.toggle("flat", flat);
  if (flat) {
    renderChecks(pinnedEl, [...byId.keys()], labels, group, {}, icon);
  } else {
    renderChecks(pinnedEl, pinnedIds.filter((id) => byId.has(id)), labels, group, {}, icon, true);
    renderChecks(fullEl, [...byId.keys()], labels, group, {}, icon);
  }
}

/** Wire an accordion section (header click flips pinned/full bodies). */
function bindAccordion(section) {
  const header = section.querySelector("[data-accordion-header]");
  if (!header || header.dataset.bound) return;
  header.dataset.bound = "1";
  header.addEventListener("click", () => {
    const open = !section.classList.contains("country-open");
    section.classList.toggle("country-open", open);
    section.querySelector("[data-acc-pinned]")?.classList.toggle("open", !open);
    section.querySelector("[data-acc-full]")?.classList.toggle("open", open);
  });
}

function applyBounds() {
  for (const [id, key] of [["yearFrom", "year_min"], ["yearTo", "year_max"], ["rtFrom", "runtime_min"],
  ["rtTo", "runtime_max"], ["budgetFrom", "budget_min"], ["budgetTo", "budget_max"]]) {
    if ($(id)) $(id).placeholder = String(bounds[key]);
  }
  const set = (id, lo, hi, value) => {
    if (!$(id)) return;
    $(id).min = lo;
    $(id).max = hi;
    $(id).value = value;
  };
  set("yearFromR", bounds.year_min, bounds.year_max, bounds.year_min);
  set("yearToR", bounds.year_min, bounds.year_max, bounds.year_max);
  set("rtFromR", bounds.runtime_min, bounds.runtime_max, bounds.runtime_min);
  set("rtToR", bounds.runtime_min, bounds.runtime_max, bounds.runtime_max);
  set("budgetFromR", bounds.budget_min, bounds.budget_max, bounds.budget_min);
  set("budgetToR", bounds.budget_min, bounds.budget_max, bounds.budget_max);
  paintDual($("yearRange"), $("yearFromR"), $("yearToR"));
  paintDual($("rtRange"), $("rtFromR"), $("rtToR"));
  paintDual($("budgetRange"), $("budgetFromR"), $("budgetToR"));
}

function mergeOptions(list) {
  const union = (key) => [...new Set(list.flatMap((o) => o[key] || []))];
  const mergeById = (key) => {
    const seen = new Map();
    for (const o of list) {
      for (const c of o[key] || []) {
        if (c?.id != null && !seen.has(String(c.id))) seen.set(String(c.id), c);
      }
    }
    return [...seen.values()];
  };
  const sumCounts = (key) => {
    const totals = {};
    for (const o of list) {
      for (const [k, v] of Object.entries(o[key] || {})) totals[k] = (totals[k] || 0) + v;
    }
    return totals;
  };
  const pick = (key, fn, d) => {
    const values = list.map((o) => o[key]).filter((v) => v != null && v !== 0);
    return values.length ? fn(...values) : d;
  };
  return {
    languages: union("languages"),
    countries: union("countries"),
    certifications: union("certifications"),
    statuses: union("statuses"),
    types: union("types"),
    genres: union("genres"),
    companies: mergeById("companies"),
    networks: mergeById("networks"),
    flag_counts: sumCounts("flag_counts"),
    country_counts: sumCounts("country_counts"),
    language_counts: sumCounts("language_counts"),
    certification_counts: sumCounts("certification_counts"),
    status_counts: sumCounts("status_counts"),
    type_counts: sumCounts("type_counts"),
    genre_counts: sumCounts("genre_counts"),
    year_min: pick("year_min", Math.min, 1900), year_max: pick("year_max", Math.max, 2030),
    runtime_min: pick("runtime_min", Math.min, 0), runtime_max: pick("runtime_max", Math.max, 300),
    episodes_min: pick("episodes_min", Math.min, 0), episodes_max: pick("episodes_max", Math.max, 100),
    budget_min: pick("budget_min", Math.min, 0), budget_max: pick("budget_max", Math.max, 500000000),
  };
}

/* ------------------------------------------------------------------ widget */

/**
 * Render the sidebar into `container` and wire it up.
 * mode: initial "movie" | "tv" | "all"; with typeSelect=false the type row is hidden
 * (index page uses its own tabs) and the mode stays fixed.
 * options/total: scoped filter options (a company page passes the options computed
 * for its own titles); the dominant country gets pre-checked.
 * Checkboxes, selects and range inputs apply immediately (debounced); onChange fires
 * after every change, Apply and Reset.
 */
export async function createFilters(container, {
  mode = "movie", onChange = () => { }, typeSelect = false, options = null, total = null,
} = {}) {
  container.innerHTML = SIDEBAR_HTML;
  const actions = document.createElement("div");
  actions.className = "filter-actions";
  actions.innerHTML = `
    <button type="button" class="btn-reset" id="btnReset">Reset</button>
    <button type="button" class="btn-apply" id="btnApply">Apply</button>`;
  const wrap = document.createElement("div");
  wrap.className = "filters-col";
  container.replaceWith(wrap);
  wrap.append(container, actions);
  const typeSel = container.querySelector("[data-role=type-select]");
  if (!typeSelect) container.querySelector('[data-kind="type"]').remove();
  else typeSel.value = mode;

  RANGES.forEach(bindDual);

  const currentType = () => (typeSelect ? typeSel.value : mode);
  const getType = () => currentType();

  const refreshVisibility = () => {
    const t = currentType();
    container.querySelectorAll(".movie-only").forEach((el) => { el.style.display = t !== "tv" ? "" : "none"; });
    container.querySelectorAll(".tv-only").forEach((el) => { el.style.display = t !== "movie" ? "" : "none"; });
    $("certLabel").textContent = t === "tv" ? "TV Parental" : "MPA";
  };

  let lastOptions = null;
  let scopedTotal = null;
  let prechecks = {};
  let autoTimer = null;

  /** Dominant country (the studio's home country) auto-checked on scoped pages. */
  const dominantCountry = (data) => {
    if (scopedTotal == null) return null;
    const counts = data.country_counts || {};
    const max = Math.max(0, ...Object.values(counts));
    if (!max) return null;
    return new Set(Object.keys(counts).filter((k) => counts[k] === max));
  };

  async function fetchOptions(t) {
    // Failed fetches are not cached: a request fired while the server was
    // restarting must not poison the sidebar until the next page reload.
    const types = t === "all" ? ["movie", "tv"] : [t];
    const loaded = await Promise.all(types.map(async (mt) => {
      if (!optionsCache[mt]) {
        optionsCache[mt] = fetch(`/api/filters?media_type=${mt}`)
          .then((r) => {
            if (!r.ok) throw new Error(`filters request failed: ${r.status}`);
            return r.json();
          })
          .catch((error) => {
            delete optionsCache[mt];
            throw error;
          });
      }
      return optionsCache[mt];
    }));
    return loaded.length === 1 ? loaded[0] : mergeOptions(loaded);
  }

  async function applyOptions(data) {
    const t = currentType();
    prechecks = { country: dominantCountry(data) };
    bounds = {
      year_min: Number(data.year_min ?? 1900), year_max: Number(data.year_max ?? 2030),
      runtime_min: Number(data.runtime_min ?? 0), runtime_max: Number(data.runtime_max ?? 300),
      budget_min: Number(data.budget_min ?? 0), budget_max: Number(data.budget_max ?? 500000000),
    };
    applyBounds();
    const available = (key) => new Set(data[key] || []);
    const orderFor = (movie, tv) =>
      t === "movie" ? movie : t === "tv" ? tv : [...movie, ...tv];

    // Collection is a pseudo-type (tri-state), shown regardless of the type values.
    renderOrderedChips($("typeChips"), orderFor(TYPE_MOVIE, TYPE_TV),
      new Set([...available("types"), "Collection"]), "type");
    renderOrderedChips($("genreChips"), orderFor(GENRES_MOVIE, GENRES_TV), available("genres"), "genre");
    renderFlagChips($("contentChips"), CONTENT, data.flag_counts);
    renderFlagChips($("nsfwChips"), NSFW, data.flag_counts);

    const iso = await getIso();
    const countryNames = {};
    const countryTitles = {};
    for (const [code, info] of Object.entries(iso.countries || {})) {
      if (typeof info === "string") countryNames[code] = info;
      else {
        countryNames[code] = info.name;
        countryTitles[code] = info.official || info.name;
      }
    }
    countryNames.SU ??= "USSR";
    countryTitles.SU ??= "the Union of Soviet Socialist Republics";

    const countries = data.countries || [];
    const countrySection = container.querySelector('[data-section="country"]');
    const countryFlat = countries.length <= FLAT_LIMIT;
    countrySection?.classList.toggle("flat", countryFlat);
    if (countrySection) countrySection.style.display = countries.length ? "" : "none";
    if (countryFlat) {
      renderChecks($("countryChips"), countries, countryNames, "country", countryTitles, true);
    } else {
      renderChecks($("countryChips"), PINNED_COUNTRIES, countryNames, "country", countryTitles, true, true, prechecks.country);
      renderChecks($("countryMore"), countries, countryNames, "country", countryTitles, true);
    }

    const langSection = container.querySelector('[data-facet="lang"]');
    langSection.style.display = (data.languages || []).length ? "" : "none";
    renderChecks($("langChips"), data.languages || [], iso.languages || {}, "lang");

    const certOrder = orderFor(CERT_MOVIE, CERT_TV);
    const certs = certOrder.filter((c) => available("certifications").has(c));
    const certSection = container.querySelector('[data-facet="cert"]');
    if (certSection) certSection.style.display = certs.length ? "" : "none";
    renderChecks($("certChips"), certs, Object.fromEntries(certs.map((c) => [c, c])), "cert");

    renderEntityAccordion(
      container.querySelector('[data-section="company"]'),
      $("companyChips"), $("companyMore"), data.companies, PINNED_COMPANIES, "company");
    renderEntityAccordion(
      container.querySelector('[data-section="network"]'),
      $("networkChips"), $("networkMore"), data.networks, PINNED_NETWORKS, "network");

    renderStatusChips($("statusFilters"), t === "all" ? "all" : t, available("statuses"), null);
    refreshVisibility();
  }

  async function loadOptions() {
    const data = await fetchOptions(currentType());
    lastOptions = data;
    scopedTotal = null;
    await applyOptions(data);
  }

  const readChecks = (group) => {
    const state = checkboxState[group] || {};
    const pre = prechecks[group];
    const values = new Set();
    for (const v of Object.keys(state)) {
      if (state[v]) values.add(v);
    }
    if (pre) {
      for (const v of pre) {
        if (!(v in state) || state[v]) values.add(v);
      }
    }
    return [...values];
  };

  function readState() {
    for (const input of container.querySelectorAll("input[data-filter-group]")) {
      // Tri-state chips (Collection, First in collection) keep their own
      // state outside checkboxState.
      if (input.dataset.filterValue in triState) continue;
      // Inputs hidden inside a collapsed accordion part must not erase
      // the state of their duplicates in the visible part (same value).
      const accBody = input.closest(".acc-body");
      if (accBody && !accBody.classList.contains("open")) continue;
      checkboxState[input.dataset.filterGroup] ??= {};
      checkboxState[input.dataset.filterGroup][input.dataset.filterValue] = input.checked;
    }
  }

  /** Filter params only; media type, q, sort and paging are the page's concern. */
  function params() {
    readState();
    const p = new URLSearchParams();
    const num = (id) => ($(id)?.value ? Number($(id).value) : null);
    const range = (id) => ($(id) ? Number($(id).value) : NaN);

    // Number inputs win over sliders; a slider not at the span edge means "clipped here".
    const spanned = [
      ["yearFrom", "yearTo", "yearFromR", "yearToR", "year_from", "year_to", bounds.year_min, bounds.year_max],
      ["rtFrom", "rtTo", "rtFromR", "rtToR", "runtime_from", "runtime_to", bounds.runtime_min, bounds.runtime_max],
      ["budgetFrom", "budgetTo", "budgetFromR", "budgetToR", "min_budget", "max_budget", bounds.budget_min, bounds.budget_max],
      ["minScore", "maxScore", "minScoreR", "maxScoreR", "min_score", "max_score", 0, 10],
    ];
    for (const [nf, nt, rf, rt, keyF, keyT, lo, hi] of spanned) {
      const f = num(nf) ?? (Number.isFinite(range(rf)) && range(rf) > lo ? range(rf) : null);
      const t = num(nt) ?? (Number.isFinite(range(rt)) && range(rt) < hi ? range(rt) : null);
      if (f != null) p.set(keyF, String(f));
      if (t != null) p.set(keyT, String(t));
    }
    if (num("epFrom") != null) p.set("episodes_from", String(num("epFrom")));
    if (num("epTo") != null) p.set("episodes_to", String(num("epTo")));
    if (num("minVotes") != null) p.set("min_votes", String(num("minVotes")));

    for (const [group, key] of [
      ["lang", "languages"], ["country", "countries"], ["cert", "certification"],
      ["type", "type"], ["genre", "genres"],
      ["company", "companies"], ["network", "networks"],
    ]) {
      const values = readChecks(group);
      if (values.length) p.set(key, values.join(","));
    }
    if (currentType() !== "tv") {
      for (const [value, param] of Object.entries(TRI_STATE_PARAMS)) {
        if (triState[value]) p.set(param, triState[value]);
      }
    }

    const features = [...container.querySelectorAll("#contentChips input[data-feature]:checked")]
      .map((i) => i.dataset.feature);
    if (features.length) p.set("features", features.join(","));
    const nsfw = [...container.querySelectorAll("#nsfwChips input[data-feature]:checked")]
      .map((i) => i.dataset.feature);
    if (nsfw.length) p.set("nsfw", nsfw.join(","));

    const statuses = [...container.querySelectorAll("#statusFilters input:checked")].map((i) => i.dataset.status);
    if (statuses.length) p.set("status", statuses.join(","));
    return p;
  }

  function reset() {
    for (const id of ["yearFrom", "yearTo", "rtFrom", "rtTo", "budgetFrom", "budgetTo",
      "minScore", "maxScore", "minVotes", "epFrom", "epTo"]) {
      if ($(id)) $(id).value = "";
    }
    checkboxState = {};
    triState = { Collection: null, "First in collection": null };
    if ($("minScoreR")) $("minScoreR").value = 0;
    if ($("maxScoreR")) $("maxScoreR").value = 10;
    paintDual($("scoreRange"), $("minScoreR"), $("maxScoreR"));
    if (lastOptions) applyOptions(lastOptions);
    else applyBounds();
  }

  // Filters apply immediately; Apply remains as an explicit button for ranges.
  const autoApply = () => {
    clearTimeout(autoTimer);
    autoTimer = setTimeout(onChange, 250);
  };
  container.addEventListener("change", (e) => {
    // Tri-state chips (Collection, First in collection): click cycles checked -> minus -> off.
    if (e.target.dataset.filterValue in triState) {
      const value = e.target.dataset.filterValue;
      triState[value] = triState[value] === null ? "yes" : triState[value] === "yes" ? "no" : null;
      e.target.checked = triState[value] === "yes";
      e.target.indeterminate = triState[value] === "no";
    }
    if (e.target.matches("input[type=checkbox], input[type=number]")) autoApply();
  });
  container.addEventListener("input", (e) => {
    if (e.target.matches("input[type=range], input[type=number]")) autoApply();
  });

  container.querySelectorAll(".filter-section").forEach((section) => {
    if (section.querySelector("[data-accordion-header]")) bindAccordion(section);
  });

  typeSel?.addEventListener("change", async () => {
    // Scoped pages (company) refresh their options themselves via setOptions.
    if (scopedTotal == null) await loadOptions();
    onChange();
  });
  $("btnApply").addEventListener("click", onChange);
  $("btnReset").addEventListener("click", () => { reset(); onChange(); });

  if (options) {
    lastOptions = options;
    scopedTotal = total ?? null;
    await applyOptions(options);
  } else {
    await loadOptions();
  }
  return {
    params,
    reset,
    getType,
    /** Replace the option set (scoped pages recompute it per media type). */
    async setOptions(opts, tot) {
      lastOptions = opts;
      scopedTotal = tot ?? null;
      await applyOptions(opts);
    },
    /** Switch the effective media type (pages with their own tabs). */
    async setMode(type) {
      mode = type;
      await loadOptions();
    },
  };
}
