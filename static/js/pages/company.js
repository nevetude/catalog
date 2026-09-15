/** Company page: company header + catalog-style grid of its movies and shows. */

import { $, esc, renderHeader, fetchJson } from "../core.js";
import { createFilters } from "../filters.js";
import { createListing, sortParams, populateSortSelect, syncSortOptions } from "../listing.js";

const companyId = Number(location.pathname.split("/").filter(Boolean)[1]);

populateSortSelect($("sortSelect"), "basic");

const listing = createListing({
  grid: $("mediaGrid"),
  search: $("searchInput"),
  sort: $("sortSelect"),
  totalEl: $("totalCount"),
  empty: $("empty"),
  onChange: () => {
    if (filterApi) syncSortOptions($("sortSelect"), filterApi.getType());
  },
  load: ({ offset, limit }) => {
    if (!filterApi) return { total: 0, items: [] };
    const params = filterApi.params();
    const { sort, order } = sortParams($("sortSelect"));
    for (const [k, v] of Object.entries({ sort, order, limit, offset })) {
      params.set(k, String(v));
    }
    return fetchJson(`/api/company/${companyId}?${params}`);
  },
});

function renderCompany(c) {
  document.title = `${c.name} – Catalog`;
  $("catalogLabel").textContent = c.name;
  $("companyHead").innerHTML = `
    ${c.logo_path ? `<img class="company-logo" src="https://image.tmdb.org/t/p/w300${esc(c.logo_path)}" alt="">` : ""}
    <h1 class="detail-title"></h1>`;
}

renderHeader();

let filterApi = null;
try {
  const head = await fetchJson(`/api/company/${companyId}?limit=1`);
  renderCompany(head.company);
  filterApi = await createFilters($("filtersCard"), {
    mode: "all",
    typeSelect: true,
    options: head.filter_options,
    total: head.total,
    onChange: async () => {
      try {
        const scoped = await fetchJson(
          `/api/company/${companyId}?limit=1&media_type=${filterApi.getType()}`);
        await filterApi.setOptions(scoped.filter_options, scoped.total);
        syncSortOptions($("sortSelect"), filterApi.getType());
      } catch (error) {
        console.error(error);
      }
      listing.reload();
    },
  });
  syncSortOptions($("sortSelect"), filterApi.getType());
  $("detailLoading").hidden = true;
  listing.reload();
} catch (error) {
  console.error(error);
  $("detailLoading").hidden = true;
  $("empty").hidden = false;
  $("empty").textContent = "Company not found";
}
