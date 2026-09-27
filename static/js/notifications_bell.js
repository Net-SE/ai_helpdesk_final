(function () {
  const bell = document.getElementById("notifBell");
  const badge = document.getElementById("notifBadge");
  if (!bell || !badge) return;

  let lastUnread = 0;

  async function refresh() {
    try {
      const r = await fetch("/notifications/api/unread/", {
        credentials: "same-origin",
      });
      if (!r.ok) return;
      const data = await r.json();

      const unread = Number(data.unread_count || 0);

      if (unread > 0) {
        badge.style.display = "inline-block";
        badge.textContent = unread;

        // ring animation only when unread increased
        if (unread > lastUnread) {
          bell.classList.remove("bell-ring");
          void bell.offsetWidth; // restart animation
          bell.classList.add("bell-ring");
        }
      } else {
        badge.style.display = "none";
        badge.textContent = "0";
      }

      lastUnread = unread;
    } catch (e) {
      // ignore errors (offline etc.)
    }
  }

  // initial + poll
  refresh();
  setInterval(refresh, 5000); // every 5 seconds
})();
