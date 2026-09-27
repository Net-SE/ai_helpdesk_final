(function () {
  const respEl = document.getElementById("slaRespCountdown");
  const resEl = document.getElementById("slaResCountdown");
  if (!respEl && !resEl) return;

  function fmt(ms) {
    const sign = ms < 0 ? "-" : "";
    ms = Math.abs(ms);
    const s = Math.floor(ms / 1000);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${sign}${h}h ${m}m ${sec}s`;
  }

  function tick() {
    const now = Date.now();

    [respEl, resEl].forEach((el) => {
      if (!el) return;
      const due = Number(el.dataset.due || "0");
      if (!due) return;
      const diff = due - now;
      el.textContent = fmt(diff);
      el.classList.toggle("text-danger", diff < 0);
      el.classList.toggle("fw-bold", diff < 0);
    });
  }

  tick();
  setInterval(tick, 1000);
})();
