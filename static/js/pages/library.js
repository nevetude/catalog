/** Library page: folder navigation + filtered folder contents. */

import { $, esc, renderHeader, fetchJson, promptFolderName } from "../core.js";
import { createFilters } from "../filters.js";
import { createListing, sortParams, populateSortSelect, syncSortOptions } from "../listing.js";

const slug = location.pathname.split("/").filter(Boolean)[1] || null;
let currentFolder = null;

populateSortSelect($("sortSelect"), "full");

async function loadFolders() {
  const data = await fetchJson("/api/library/folders");
  const folders = data.folders || [];
  currentFolder = folders.find((f) => f.slug === slug) || folders[0];
  $("folderNav").innerHTML = `
    <div class="folder-nav-left">
      ${folders.map((f) => `
        <a class="folder-pill ${currentFolder?.id === f.id ? "active" : ""}"
           href="/library/${f.slug}">${esc(f.name)} <span>${f.item_count}</span></a>`).join("")}
    </div>
    <button type="button" class="btn-ghost" id="btnNewFolder">+ New folder</button>`;
  $("btnNewFolder").addEventListener("click", async () => {
    const name = await promptFolderName();
    if (!name) return;
    await fetchJson("/api/library/folders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    await loadFolders();
    listing.reload();
  });
}

const listing = createListing({
  grid: $("mediaGrid"),
  search: $("searchInput"),
  sort: $("sortSelect"),
  totalEl: $("totalCount"),
  empty: $("empty"),
  onChange: loadFolders,
  load: ({ offset, limit }) => {
    if (!currentFolder) return { total: 0, items: [] };
    const params = filterApi.params();
    const { sort, order } = sortParams($("sortSelect"));
    for (const [k, v] of Object.entries({ sort, order, limit, offset })) {
      params.set(k, String(v));
    }
    return fetchJson(`/api/library/folders/${currentFolder.id}/items?${params}`);
  },
});

renderHeader();

let filterApi = null;
try {
  await loadFolders();
  $("catalogLabel").textContent = currentFolder?.name || "Library";
  filterApi = await createFilters($("filtersCard"), {
    mode: "all",
    typeSelect: true,
    onChange: () => {
      syncSortOptions($("sortSelect"), filterApi.getType());
      listing.reload();
    },
  });
  syncSortOptions($("sortSelect"), filterApi.getType());
  listing.reload();
} catch (error) {
  console.error(error);
  location.href = "/login";
}
