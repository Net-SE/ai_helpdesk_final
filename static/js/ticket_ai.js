(() => {
  const form = document.getElementById("ticketCreateForm");
  if (!form) return;

  const titleInput = form.querySelector('input[name="title"]');
  const descInput = form.querySelector('textarea[name="description"]');
  const categorySelect = form.querySelector('select[name="category"]');
  const prioritySelect = form.querySelector('select[name="priority"]');

  const aiBox = document.getElementById("aiBox");
  const aiCategory = document.getElementById("aiCategory");
  const aiPriority = document.getElementById("aiPriority");
  const aiKb = document.getElementById("aiKb");
  const aiConfidence = document.getElementById("aiConfidence"); // optional
  const aiSteps = document.getElementById("aiSteps"); // optional

  let timer = null;
  let categoryTouched = false;
  let priorityTouched = false;

  if (categorySelect) {
    categorySelect.addEventListener("change", () => {
      categoryTouched = true;
    });
  }
  if (prioritySelect) {
    prioritySelect.addEventListener("change", () => {
      priorityTouched = true;
    });
  }

  function setVisible(el, visible) {
    if (!el) return;
    el.style.display = visible ? "block" : "none";
  }

  function clearList(el) {
    if (!el) return;
    el.innerHTML = "";
  }

  function renderList(el, items, renderItem) {
    if (!el) return;
    clearList(el);
    (items || []).forEach((item) => {
      const li = document.createElement("li");
      renderItem(li, item);
      el.appendChild(li);
    });
  }

  function getText() {
    const t = (titleInput?.value || "").trim();
    const d = (descInput?.value || "").trim();
    return (t + "\n" + d).trim();
  }

  async function fetchSuggestions(text) {
    const url = "/ai/suggest/?text=" + encodeURIComponent(text);
    const res = await fetch(url, { credentials: "same-origin" });
    return await res.json();
  }

  function applySuggestions(data) {
    // show box
    setVisible(aiBox, true);

    // set category/priority labels
    if (aiCategory) aiCategory.textContent = data.category || "";
    if (aiPriority) aiPriority.textContent = data.priority || "";

    // confidence
    if (aiConfidence)
      aiConfidence.textContent = (data.confidence ?? "").toString();

    // auto-fill selects only if user hasn't manually changed them
    if (categorySelect && !categoryTouched && data.category)
      categorySelect.value = data.category;
    if (prioritySelect && !priorityTouched && data.priority)
      prioritySelect.value = data.priority;

    // KB list
    renderList(aiKb, data.kb, (li, a) => {
      li.innerHTML = `<a href="/kb/${a.id}/" target="_blank" rel="noopener">${a.title}</a>`;
    });

    // Steps list (optional)
    renderList(aiSteps, data.steps, (li, step) => {
      li.textContent = step;
    });
  }

  async function run() {
    const text = getText();
    if (text.length < 5) {
      setVisible(aiBox, false);
      return;
    }

    try {
      const data = await fetchSuggestions(text);
      applySuggestions(data);
    } catch (e) {
      // fail silently
      // you could show aiBox with fallback info if you want
    }
  }

  function schedule() {
    if (timer) clearTimeout(timer);
    timer = setTimeout(run, 400);
  }

  titleInput?.addEventListener("input", schedule);
  descInput?.addEventListener("input", schedule);
})();
