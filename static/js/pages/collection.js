/** Collection page: catalog-style grid of the movies in one collection. */

import { $, esc, renderHeader, fetchJson } from "../core.js";
import { createFilters } from "../filters.js";
import { createListing, sortParams, populateSortSelect, syncSortOptions } from "../listing.js";

const collectionId = Number(location.pathname.split("/").filter(Boolean)[1]);

populateSortSelect($("sortSelect"), "full");
syncSortOptions($("sortSelect"), "movie");  // collections contain movies only

const listing = createListing({
  grid: $("mediaGrid"),
  search: $("searchInput"),
  sort: $("sortSelect"),
  totalEl: $("totalCount"),
  empty: $("empty"),
  load: ({ offset, limit }) => {
    if (!filterApi) return { total: 0, items: [] };
    const params = filterApi.params();
    const { sort, order } = sortParams($("sortSelect"));
    for (const [k, v] of Object.entries({ sort, order, limit, offset })) {
      params.set(k, String(v));
    }
    return fetchJson(`/api/collection/${collectionId}?${params}`);
  },
});

renderHeader();

let filterApi = null;
try {
  const head = await fetchJson(`/api/collection/${collectionId}?limit=1`);
  document.title = `${head.collection.name} – Catalog`;
  $("catalogLabel").textContent = head.collection.name;
  filterApi = await createFilters($("filtersCard"), { mode: "movie", onChange: () => listing.reload() });
  listing.reload();
} catch (error) {
  console.error(error);
  $("empty").hidden = false;
  $("empty").textContent = "Collection not found";
}
