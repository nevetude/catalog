/** Person page: bio header + filmography grid scoped to that person. */

import { $, esc, renderHeader, fetchJson, formatDate } from "../core.js";
import { createFilters } from "../filters.js";
import { createListing, sortParams, populateSortSelect } from "../listing.js";

const personId = Number(location.pathname.split("/").filter(Boolean)[1]);
let roles = [];

$("kindSelect").innerHTML = `
  <option value="">All</option>
  <option value="movie">Movies</option>
  <option value="feature">Feature films</option>
  <option value="short">Shorts</option>
  <option value="tv">TV Shows</option>`;
populateSortSelect($("sortSelect"), "person");

const listing = createListing({
  grid: $("mediaGrid"),
  search: $("searchInput"),
  sort: $("sortSelect"),
  totalEl: $("totalCount"),
  empty: $("empty"),
  load: ({ offset, limit }) => {
    if (!filterApi) return { total: 0, items: [] };
    const params = filterApi.params();
    params.set("media_kind", $("kindSelect").value);
    if ($("roleSelect").value) params.set("role", $("roleSelect").value);
    const { sort, order } = sortParams($("sortSelect"));
    for (const [k, v] of Object.entries({ sort, order, offset })) {
      params.set(k, String(v));
    }
    params.set("limit", String(limit));
    return fetchJson(`/api/person/${personId}?${params}`);
  },
});

function renderPerson(p) {
  document.title = `${p.name} – Catalog`;
  const facts = [];
  if (p.known_for_department) facts.push(["Known for", p.known_for_department]);
  if (p.birthday) facts.push(["Born", formatDate(p.birthday)]);
  if (p.place_of_birth) facts.push(["Place of birth", p.place_of_birth]);
  $("personHead").innerHTML = `
    <div class="detail-poster">${p.profile ? `<img src="${esc(p.profile)}" alt="" fetchpriority="high">` : ""}</div>
    <div class="detail-info">
      <h1 class="detail-title">${esc(p.name)}</h1>
      ${p.biography ? `<p class="detail-overview">${esc(p.biography)}</p>` : ""}
      ${facts.length ? `<div class="detail-grid">${facts.map(([k, v]) =>
        `<div class="fact"><div class="fact-label">${esc(k)}</div><div class="fact-value">${esc(v)}</div></div>`
      ).join("")}</div>` : ""}
    </div>`;
  $("roleSelect").innerHTML = `<option value="">All roles</option>` +
    roles.map((r) => `<option value="${esc(r)}">${esc(r)}</option>`).join("");
}

renderHeader();

let filterApi = null;
try {
  const personData = await fetchJson(`/api/person/${personId}?limit=1`);
  renderPerson(personData.person);
  roles = personData.roles || [];
  filterApi = await createFilters($("filtersCard"), { mode: "all", typeSelect: false, onChange: () => listing.reload() });
  $("detailLoading").hidden = true;
  $("detailRoot").hidden = false;
  listing.reload();
} catch (error) {
  console.error(error);
  $("detailLoading").hidden = true;
  $("detailError").hidden = false;
}

$("kindSelect").addEventListener("change", () => listing.reload());
$("roleSelect").addEventListener("change", () => listing.reload());
