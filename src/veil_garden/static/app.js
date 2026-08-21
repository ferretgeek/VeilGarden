(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const themeNames = { sky: "天青", jade: "翡翠", sunset: "晚霞", graphite: "深灰" };
  const state = { token: "", reveal: false, aliases: [], stats: {}, events: [], editing: null, removing: null };

  function toast(message, type = "ok") {
    const item = document.createElement("div");
    item.className = `toast ${type === "error" ? "error" : ""}`;
    item.textContent = message;
    $("#toastRegion").append(item);
    window.setTimeout(() => item.remove(), 3600);
  }

  function setTheme(theme) {
    if (!Object.hasOwn(themeNames, theme)) theme = "sky";
    document.body.dataset.theme = theme;
    localStorage.setItem("veil-garden-theme", theme);
    $("meta[name='theme-color']").content = theme === "graphite" ? "#17191d" : "#edf5f3";
    $("#themeButton").setAttribute("aria-label", `选择主题，当前${themeNames[theme]}`);
    $$('[data-theme-choice]').forEach((button) => {
      button.setAttribute("aria-current", String(button.dataset.themeChoice === theme));
    });
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${state.token}`);
    if (options.body && !(options.body instanceof Blob)) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, headers, cache: "no-store" });
    if (response.status === 401) {
      $("#accessGate").hidden = false;
      throw new Error("访问令牌无效或已经过期");
    }
    if (!response.ok) {
      let message = "请求未能完成";
      try {
        const payload = await response.json();
        if (payload.error) message = payload.error;
      } catch (_error) {
        // Keep the safe generic message for non-JSON failures.
      }
      throw new Error(message);
    }
    return response;
  }

  function formatTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "刚刚";
    return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  function makeTag(text) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = text;
    return tag;
  }

  function renderAliases() {
    const list = $("#aliasList");
    list.replaceChildren();
    const query = $("#searchInput").value.trim().toLocaleLowerCase();
    const status = $("#statusFilter").value;
    const visible = state.aliases.filter((item) => {
      const statusMatch = status === "all" || item.status === status;
      const haystack = [item.address, item.label, item.note, ...(item.tags || [])].join(" ").toLocaleLowerCase();
      return statusMatch && (!query || haystack.includes(query));
    });
    $("#resultCount").textContent = `${visible.length} 枚地址`;
    $("#emptyState").hidden = visible.length !== 0;
    for (const item of visible) {
      const row = document.createElement("article");
      row.className = "alias-row";
      const address = document.createElement("div");
      address.className = "alias-address";
      const strong = document.createElement("strong");
      strong.textContent = item.address;
      strong.title = item.address;
      const small = document.createElement("small");
      small.textContent = item.label || "等待命名";
      address.append(strong, small);

      const note = document.createElement("div");
      note.className = "alias-note";
      note.textContent = item.note || "没有备注";
      note.title = item.note || "没有备注";

      const tags = document.createElement("div");
      tags.className = "tag-list";
      (item.tags || []).slice(0, 3).forEach((tag) => tags.append(makeTag(tag)));
      if (!(item.tags || []).length) tags.append(makeTag("未分类"));

      const statusPill = document.createElement("span");
      statusPill.className = `status-pill ${item.status}`;
      statusPill.textContent = item.status === "active" ? "使用中" : "休眠";

      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "edit-button";
      edit.dataset.aliasId = item.id;
      edit.setAttribute("aria-label", `整理 ${item.label || "这枚地址"}`);
      edit.textContent = "⋯";
      row.append(address, note, tags, statusPill, edit);
      list.append(row);
    }
  }

  function renderEvents() {
    const list = $("#eventList");
    list.replaceChildren();
    const events = state.events.slice(0, 6);
    if (!events.length) {
      const empty = document.createElement("div");
      empty.className = "event-item";
      const text = document.createElement("strong");
      text.textContent = "等待第一次整理";
      empty.append(text);
      list.append(empty);
      return;
    }
    for (const event of events) {
      const item = document.createElement("div");
      item.className = "event-item";
      const detail = document.createElement("strong");
      detail.textContent = event.detail;
      const time = document.createElement("time");
      time.dateTime = event.created_at;
      time.textContent = formatTime(event.created_at);
      item.append(detail, time);
      list.append(item);
    }
  }

  function render() {
    $("#statTotal").textContent = state.stats.total ?? "—";
    $("#statActive").textContent = state.stats.active ?? "—";
    $("#statResting").textContent = state.stats.resting ?? "—";
    $("#statUnlabeled").textContent = state.stats.unlabeled ?? "—";
    $("#privacyHint").textContent = state.reveal ? "完整地址仅在当前视图出现" : "地址默认遮罩";
    $("#privacyButton").setAttribute("aria-label", state.reveal ? "重新遮罩地址" : "揭开地址遮罩");
    renderAliases();
    renderEvents();
  }

  async function loadGarden() {
    const response = await api(`/api/bootstrap?reveal=${state.reveal ? "1" : "0"}`);
    const payload = await response.json();
    state.aliases = payload.aliases || [];
    state.stats = payload.stats || {};
    state.events = payload.events || [];
    while (state.aliases.length < (state.stats.total || 0)) {
      const responsePage = await api(`/api/aliases?reveal=${state.reveal ? "1" : "0"}&limit=500&offset=${state.aliases.length}`);
      const page = await responsePage.json();
      const batch = page.aliases || [];
      if (!batch.length) break;
      state.aliases.push(...batch);
    }
    $("#officialLink").href = payload.officialGuide;
    $("#modeLabel").textContent = payload.demo ? "SYNTHETIC DEMO" : "LOCAL-FIRST";
    $("#accessGate").hidden = true;
    render();
  }

  function openDialog(id) {
    const dialog = $(`#${id}`);
    if (!dialog.open) dialog.showModal();
  }

  function resetAliasForm() {
    state.editing = null;
    $("#aliasForm").reset();
    $("#aliasId").value = "";
    $("#aliasDialogTitle").textContent = "添加地址";
    $("#removeButton").hidden = true;
  }

  async function rawAlias(aliasId) {
    const response = await api("/api/aliases?reveal=1&limit=500");
    const payload = await response.json();
    return (payload.aliases || []).find((item) => item.id === aliasId);
  }

  async function editAlias(aliasId) {
    try {
      const item = await rawAlias(aliasId);
      if (!item) throw new Error("找不到这条记录");
      state.editing = item;
      $("#aliasId").value = item.id;
      $("#addressInput").value = item.address;
      $("#labelInput").value = item.label;
      $("#aliasStatus").value = item.status;
      $("#tagsInput").value = (item.tags || []).join(", ");
      $("#noteInput").value = item.note;
      $("#aliasDialogTitle").textContent = "整理这枚地址";
      $("#removeButton").hidden = false;
      openDialog("aliasDialog");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function aliasPayload() {
    return {
      address: $("#addressInput").value,
      label: $("#labelInput").value,
      status: $("#aliasStatus").value,
      tags: $("#tagsInput").value.split(",").map((item) => item.trim()).filter(Boolean),
      note: $("#noteInput").value,
    };
  }

  function parseImport(text) {
    return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).slice(0, 5001).map((line) => {
      const [address = "", label = "", tags = ""] = line.split("|").map((item) => item.trim());
      return { address, label, tags: tags.split(",").map((item) => item.trim()).filter(Boolean), status: "active" };
    });
  }

  async function downloadExport(format, full) {
    const headers = full ? { "X-Export-Confirmation": "EXPORT FULL" } : {};
    const response = await api(`/api/export?format=${encodeURIComponent(format)}`, { headers });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `veil-garden.${format}`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function bindEvents() {
    $("#themeButton").addEventListener("click", () => {
      const menu = $("#themeMenu");
      menu.hidden = !menu.hidden;
      $("#themeButton").setAttribute("aria-expanded", String(!menu.hidden));
    });
    $$('[data-theme-choice]').forEach((button) => button.addEventListener("click", () => {
      setTheme(button.dataset.themeChoice);
      $("#themeMenu").hidden = true;
      $("#themeButton").setAttribute("aria-expanded", "false");
    }));
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".theme-wrap")) {
        $("#themeMenu").hidden = true;
        $("#themeButton").setAttribute("aria-expanded", "false");
      }
    });
    $("#privacyButton").addEventListener("click", async () => {
      state.reveal = !state.reveal;
      try { await loadGarden(); } catch (error) { state.reveal = !state.reveal; toast(error.message, "error"); }
    });
    $("#addButton").addEventListener("click", () => { resetAliasForm(); openDialog("aliasDialog"); });
    $$('[data-action="open-add"]').forEach((button) => button.addEventListener("click", () => { resetAliasForm(); openDialog("aliasDialog"); }));
    $("#importButton").addEventListener("click", () => openDialog("importDialog"));
    $("#exportButton").addEventListener("click", () => openDialog("exportDialog"));
    $$('[data-close-dialog]').forEach((button) => button.addEventListener("click", () => $(`#${button.dataset.closeDialog}`).close()));
    $("#searchInput").addEventListener("input", renderAliases);
    $("#statusFilter").addEventListener("change", renderAliases);
    $("#aliasList").addEventListener("click", (event) => {
      const button = event.target.closest("[data-alias-id]");
      if (button) editAlias(button.dataset.aliasId);
    });

    $("#accessForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      state.token = $("#tokenInput").value.trim();
      $("#accessError").textContent = "";
      try { await loadGarden(); } catch (error) { $("#accessError").textContent = error.message; }
    });

    $("#aliasForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const id = $("#aliasId").value;
      try {
        await api(id ? `/api/aliases/${id}` : "/api/aliases", { method: id ? "PATCH" : "POST", body: JSON.stringify(aliasPayload()) });
        $("#aliasDialog").close();
        toast(id ? "这枚地址已经重新整理" : "一枚新地址已经入园");
        await loadGarden();
      } catch (error) { toast(error.message, "error"); }
    });

    $("#removeButton").addEventListener("click", () => {
      if (!state.editing) return;
      state.removing = state.editing;
      const phrase = `REMOVE ${state.editing.id}`;
      $("#removePhrase").textContent = phrase;
      $("#removeConfirm").value = "";
      $("#aliasDialog").close();
      openDialog("removeDialog");
    });
    $("#removeForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!state.removing) return;
      const phrase = `REMOVE ${state.removing.id}`;
      if ($("#removeConfirm").value !== phrase) { toast("确认短语不完全一致", "error"); return; }
      try {
        await api(`/api/aliases/${state.removing.id}`, { method: "DELETE", headers: { "X-Remove-Confirmation": phrase } });
        $("#removeDialog").close();
        toast("本地记录已经移除");
        await loadGarden();
      } catch (error) { toast(error.message, "error"); }
    });

    $("#importText").addEventListener("input", () => {
      const rows = parseImport($("#importText").value);
      $("#importPreview").textContent = rows.length ? `准备导入 ${rows.length} 行` : "等待输入";
    });
    $("#importFile").addEventListener("change", async () => {
      const file = $("#importFile").files[0];
      if (!file) return;
      if (file.size > 256 * 1024) { toast("文件不能超过 256 KiB", "error"); return; }
      $("#importText").value = await file.text();
      $("#importText").dispatchEvent(new Event("input"));
    });
    $("#importForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const aliases = parseImport($("#importText").value);
      if (!aliases.length) { toast("请先粘贴或选择地址文件", "error"); return; }
      if (aliases.length > 5000) { toast("一次最多导入 5000 行", "error"); return; }
      try {
        const response = await api("/api/import", { method: "POST", body: JSON.stringify({ aliases }) });
        const result = await response.json();
        $("#importDialog").close();
        $("#importForm").reset();
        $("#importPreview").textContent = "等待输入";
        toast(`导入 ${result.imported} 条，跳过 ${result.duplicates} 条重复与 ${result.invalid} 条无效记录`);
        await loadGarden();
      } catch (error) { toast(error.message, "error"); }
    });

    $("#fullExport").addEventListener("change", () => {
      $("#exportConfirmWrap").hidden = !$("#fullExport").checked;
      $("#exportConfirm").value = "";
    });
    $("#exportForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const format = $("input[name='exportFormat']:checked").value;
      const full = $("#fullExport").checked;
      if (full && $("#exportConfirm").value !== "EXPORT FULL") { toast("完整导出确认短语不一致", "error"); return; }
      try {
        await downloadExport(format, full);
        $("#exportDialog").close();
        toast(full ? "完整副本已经下载，请妥善保管" : "遮罩副本已经下载");
      } catch (error) { toast(error.message, "error"); }
    });
  }

  async function start() {
    setTheme(localStorage.getItem("veil-garden-theme") || "sky");
    bindEvents();
    const fragment = new URLSearchParams(location.hash.replace(/^#/, ""));
    const fragmentToken = fragment.get("token");
    if (fragmentToken) {
      state.token = fragmentToken;
      history.replaceState(null, "", `${location.pathname}${location.search}`);
    }
    if (!state.token) { $("#accessGate").hidden = false; return; }
    try { await loadGarden(); } catch (error) { $("#accessError").textContent = error.message; }
  }

  start();
})();
