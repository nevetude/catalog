/** Theme boot: runs synchronously from <head> to avoid a flash of the wrong theme. */
(function () {
  var stored = null;
  try { stored = localStorage.getItem("theme"); } catch (e) { /* storage unavailable */ }
  var dark = stored === "dark"
    || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) document.documentElement.setAttribute("data-theme", "dark");
})();
