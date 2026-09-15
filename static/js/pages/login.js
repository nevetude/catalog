/** Login / register page. */

import { $, renderHeader, fetchJson } from "../core.js";

async function go(path) {
  const err = $("authError");
  err.hidden = true;
  try {
    await fetchJson(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });
    location.href = "/";
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
}

$("btnLogin").addEventListener("click", () => go("/api/auth/login"));
$("btnRegister").addEventListener("click", () => go("/api/auth/register"));
renderHeader();
