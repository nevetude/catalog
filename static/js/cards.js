/** Media card rendering shared by all listing pages. */

import {
  esc,
  scoreColor,
  certClass,
  formatRuntime,
  CERT_TIP,
} from "./core.js";

function itemHref(item) {
  return item.media_type === "movie" ? `/movie/${item.id}` : `/show/${item.id}`;
}

export function mediaCard(item, index) {
  const rating = item.vote_average > 0 ? `
    <span class="rating-badge" style="background:${scoreColor(item.vote_average)}"
          title="${(item.vote_count || 0).toLocaleString()} votes">${item.vote_average}</span>` : "";
  const cert = item.certification ? `
    <span class="cert-badge ${certClass(item.certification)}"
          title="${esc(CERT_TIP[item.certification] || "")}">${esc(item.certification)}</span>` : "";
  const directors = (item.directors || []).join(", ");
  const genres = (item.genres || []).slice(0, 4).join(", ");
  const titleTip = item.original_title && item.original_title !== item.title ? esc(item.original_title) : "";
  const metaLeft = [item.type || (item.media_type === "movie" ? "Movie" : "TV"), item.year]
    .filter(Boolean).join(" · ");
  const metaRight = item.media_type === "movie"
    ? formatRuntime(item.runtime)
    : (item.episodes ? `${item.episodes} ep` : "");
  const flags = [
    item.in_watched ? `<span class="flag-pill flag-watched" title="Watched">WATCHED</span>` : "",
    item.in_watchlist ? `<span class="flag-pill flag-watchlist" title="Watchlist">LIST</span>` : "",
  ].filter(Boolean).join("");
  // Above-the-fold posters load eagerly (the first one is the LCP candidate);
  // everything below scrolls in lazily.
  const imgAttrs = index == null ? 'loading="lazy"'
    : index === 0 ? 'loading="eager" fetchpriority="high"'
    : index < 4 ? 'loading="eager"' : 'loading="lazy"';
  const poster = item.poster
    ? `<img src="${esc(item.poster)}" alt="" ${imgAttrs}>`
    : `<div class="poster-placeholder">${esc(item.title || "?")}</div>`;
  const role = item.role ? `<div class="ov-dir">${esc(item.role)}</div>` : "";

  return `
    <div class="media-card">
      <div class="poster-wrapper">
        <a class="poster-link" href="${esc(itemHref(item))}">
          ${poster}
          ${rating}
          ${cert}
          <div class="card-overlay">
            ${role}
            ${directors ? `<div class="ov-dir">${esc(directors)}</div>` : ""}
            ${genres ? `<div class="ov-genres">${esc(genres)}</div>` : ""}
          </div>
          ${flags ? `<div class="folder-flags">${flags}</div>` : ""}
        </a>
        <button type="button" class="card-add" data-type="${esc(item.media_type)}"
                data-id="${esc(item.id)}" title="Edit library folders">+</button>
      </div>
      <div class="media-card-body">
        <div class="media-title" ${titleTip ? `title="${titleTip}"` : ""}>${esc(item.title)}</div>
        <div class="media-meta">
          <span class="meta-left">${esc(metaLeft)}</span>
          <span class="meta-right">${esc(metaRight)}</span>
        </div>
      </div>
    </div>`;
}

export function renderItems(grid, items, { append = false, startIndex = 0 } = {}) {
  const html = items.map((item, i) => mediaCard(item, startIndex + i)).join("");
  if (append) grid.insertAdjacentHTML("beforeend", html);
  else grid.innerHTML = html;
}

export function skeletonCards(count = 10) {
  return Array.from({ length: count }, () => `
    <div class="media-card skeleton-card">
      <div class="poster-wrapper skeleton-block"></div>
      <div class="media-card-body">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
      </div>
    </div>`).join("");
}
