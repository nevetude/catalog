/** Index page: full catalog with movie/tv tabs. */

import { $, renderHeader } from "../core.js";
import { createFilters } from "../filters.js";
import { createListing, sortParams, populateSortSelect, syncSortOptions } from "../listing.js";

let mediaType = "movie";
let filterApi = null;

populateSortSelect($("sortSelect"), "full");

const listing = createListing({
  grid: $("mediaGrid"),
  search: $("searchInput"),
  sort: $("sortSelect"),
  totalEl: $("totalCount"),
  empty: $("empty"),
  load: ({ offset, limit }) => {
    const params = filterApi.params();
    params.set("media_type", mediaType);
    const { sort, order } = sortParams($("sortSelect"));
    params.set("sort", sort);
    params.set("order", order);
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    return fetch(`/api/catalog?${params}`).then((r) => {
      if (!r.ok) throw new Error(`Catalog request failed: ${r.status}`);
      return r.json();
    });
  },
});

async function setTab(type) {
  mediaType = type;
  $("tabMovies").classList.toggle("active", type === "movie");
  $("tabShows").classList.toggle("active", type === "tv");
  $("catalogLabel").textContent = type === "movie" ? "Movies" : "TV Shows";
  syncSortOptions($("sortSelect"), type);
  await filterApi.setMode(type);
  listing.reload();
}
renderHeader({
  nav: `<a href="#" class="nav-tab active" id="tabMovies">Movies</a>
        <a href="#" class="nav-tab" id="tabShows">TV Shows</a>`,
});

$("tabMovies").addEventListener("click", (e) => { e.preventDefault(); setTab("movie"); });
$("tabShows").addEventListener("click", (e) => { e.preventDefault(); setTab("tv"); });



filterApi = await createFilters($("filtersCard"), { mode: "movie", onChange: () => listing.reload() })
  .catch(async (error) => {
    console.error("Failed to load filters:", error);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return createFilters($("filtersCard"), { mode: "movie", onChange: () => listing.reload() });
  });
syncSortOptions($("sortSelect"), mediaType);
listing.reload();
