/** Generic paged listing with search, sort and infinite scroll. */

import { skeletonCards, renderItems } from "./cards.js";
import { openFolderPicker } from "./core.js";

const PAGE_SIZE = 40;

/**
 * Wire a catalog-card area (search, sort, grid, empty, total) to a loader.
 * load({ offset, limit }) must resolve {total, items}.
 * Returns { reload }; call it after external changes (see onChange).
 */
export function createListing({ grid, search, sort, totalEl, empty, load, onChange }) {
  let offset = 0;
  let total = 0;
  let busy = false;
  let searchTimer = null;

  async function fetchPage({ append = false } = {}) {
    if (append && (busy || offset >= total)) return;
    busy = true;
    if (!append) {
      offset = 0;
      total = 0;
      empty.hidden = true;
      grid.innerHTML = skeletonCards(10);
    }
    try {
      const data = await load({
        offset: append ? offset : 0,
        limit: PAGE_SIZE,
      });
      total = Number(data.total ?? 0);
      if (totalEl) totalEl.textContent = String(total);
      const items = Array.isArray(data.items) ? data.items : [];
      if (!append && items.length === 0) {
        grid.innerHTML = "";
        empty.hidden = false;
        return;
      }
      renderItems(grid, items, { append, startIndex: offset });
      offset += items.length;
      if (items.length < PAGE_SIZE) offset = total;
    } catch (error) {
      console.error("Failed to load listing:", error);
      if (!append) {
        grid.innerHTML = "";
        empty.hidden = false;
        empty.textContent = "Failed to load";
      }
    } finally {
      busy = false;
      if (offset < total) requestAnimationFrame(checkScroll);
    }
  }

  function checkScroll() {
    if (busy || offset >= total) return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 600) {
      fetchPage({ append: true });
    }
  }

  window.addEventListener("scroll", checkScroll, { passive: true });

  search?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => fetchPage(), 300);
  });
  sort?.addEventListener("change", () => fetchPage());

  grid.addEventListener("click", async (event) => {
    const button = event.target.closest(".card-add");
    if (!button) return;
    event.preventDefault();
    try {
      await openFolderPicker(button.dataset.type, Number(button.dataset.id));
      if (onChange) await onChange();
      fetchPage();
    } catch (error) {
      console.error("Failed to update library:", error);
    }
  });

  return { reload: () => fetchPage() };
}

export function sortParams(sortSelect) {
  const sort = sortSelect?.value || "vote_count";
  return { sort, order: sort === "name" ? "asc" : "desc" };
}

/** Sort option sets shared by the listing pages (HTML keeps only an empty <select>). */
const SORT_VARIANTS = {
  full: [
    ["vote_count", "Votes"], ["vote_average", "Rating"], ["popularity", "Popularity"],
    ["name", "Alphabetically"], ["year", "By date"], ["runtime", "By runtime"],
    ["budget", "By budget"], ["revenue", "By revenue"], ["episodes", "By episodes"],
  ],
  basic: [
    ["vote_count", "Votes"], ["vote_average", "Rating"], ["popularity", "Popularity"],
    ["name", "Alphabetically"], ["year", "By date"],
  ],
};

/** Fill a sort <select> with one of the SORT_VARIANTS option sets. */
export function populateSortSelect(select, variant = "full") {
  if (!select) return;
  select.innerHTML = SORT_VARIANTS[variant].map(([value, label], i) =>
    `<option value="${value}"${i === 0 ? " selected" : ""}>${label}</option>`
  ).join("");
}

/**
 * Hide sort options unsupported by the current media type
 * (movie-only: runtime/budget/revenue, tv-only: episodes).
 */
export function syncSortOptions(sortSelect, mediaType) {
  if (!sortSelect) return;
  const groups = {
    movie: ["runtime", "budget", "revenue"],
    tv: ["episodes"],
  };
  for (const option of sortSelect.options) {
    if (!option.value) continue;
    const value = option.value;
    const isMovieOnly = groups.movie.includes(value);
    const isTvOnly = groups.tv.includes(value);
    if (mediaType === "tv" && isMovieOnly) option.hidden = true;
    else if (mediaType === "movie" && isTvOnly) option.hidden = true;
    else option.hidden = false;
  }
  if (sortSelect.selectedOptions[0]?.hidden) sortSelect.value = "vote_count";
}
