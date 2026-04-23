const state = {
  config: null,
  items: [],
  selectedId: null,
  uploading: false,
};

const els = {
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("file-input"),
  uploadHint: document.getElementById("upload-hint"),
  queue: document.getElementById("queue"),
  emptyHint: document.getElementById("empty-hint"),
  preview: document.getElementById("preview"),
  previewTitle: document.getElementById("preview-title"),
  downloadAll: document.getElementById("download-all"),
  downloadCurrent: document.getElementById("download-current"),
  copyMd: document.getElementById("copy-md"),
  refresh: document.getElementById("refresh"),
  retentionHint: document.getElementById("retention-hint"),
  llmStatus: document.getElementById("llm-status"),
  toast: document.getElementById("toast"),
  tpl: document.getElementById("queue-item-template"),
};

function showToast(message, variant = "info") {
  els.toast.textContent = message;
  els.toast.className = `toast show ${variant}`;
  window.clearTimeout(showToast._t);
  showToast._t = window.setTimeout(() => {
    els.toast.classList.remove("show");
  }, 2800);
}

function formatBytes(n) {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

async function loadConfig() {
  const res = await fetch("/api/config");
  const data = await res.json();
  state.config = data;
  els.uploadHint.textContent = `개별 최대 ${data.maxFileSizeMB}MB, 한 번에 ${data.maxFilesPerUpload}개까지 업로드 가능합니다.`;
  if (data.retentionHours > 0) {
    els.retentionHint.textContent = `변환된 파일은 ${data.retentionHours}시간 후 자동으로 삭제됩니다.`;
  } else {
    els.retentionHint.textContent = "자동 정리 기능이 꺼져 있습니다.";
  }

  const status = els.llmStatus;
  const label = status.querySelector(".label");
  if (data.llm && data.llm.enabled) {
    status.classList.add("on");
    status.classList.remove("off");
    label.textContent = `LLM 활성 · ${data.llm.modelName}`;
  } else {
    status.classList.add("off");
    status.classList.remove("on");
    label.textContent = "LLM 비활성 (.env 설정 필요)";
  }
}

async function loadHistory() {
  const res = await fetch("/api/history");
  const data = await res.json();
  state.items = data.items || [];
  renderQueue();
}

function renderQueue() {
  els.queue.innerHTML = "";
  const okCount = state.items.filter((it) => it.status === "ok").length;
  els.downloadAll.disabled = okCount === 0;
  els.emptyHint.style.display = state.items.length === 0 ? "block" : "none";

  for (const item of state.items) {
    const node = els.tpl.content.firstElementChild.cloneNode(true);
    node.dataset.id = item.id;

    const nameEl = node.querySelector(".item-name");
    nameEl.textContent = item.originalName;
    nameEl.title = item.originalName;

    const meta = node.querySelector(".item-meta");
    meta.innerHTML = "";
    if (item.status === "ok") {
      const tag = document.createElement("span");
      tag.className = "tag ok";
      tag.textContent = "완료";
      meta.appendChild(tag);
    } else if (item.status === "error") {
      const tag = document.createElement("span");
      tag.className = "tag error";
      tag.textContent = "실패";
      meta.appendChild(tag);
    } else {
      const tag = document.createElement("span");
      tag.className = "tag pending";
      tag.textContent = "처리 중";
      meta.appendChild(tag);
    }
    if (item.llmUsed) {
      const tag = document.createElement("span");
      tag.className = "tag llm";
      tag.textContent = "LLM";
      meta.appendChild(tag);
    }
    const time = document.createElement("span");
    time.textContent = formatTime(item.createdAt);
    meta.appendChild(time);
    if (item.status === "ok") {
      const size = document.createElement("span");
      size.textContent = formatBytes(item.sizeBytes);
      meta.appendChild(size);
    }
    if (item.status === "error" && item.error) {
      const err = document.createElement("span");
      err.textContent = `— ${item.error}`;
      err.style.color = "var(--danger)";
      meta.appendChild(err);
    }

    const btnPreview = node.querySelector(".btn-preview");
    const btnDownload = node.querySelector(".btn-download");
    if (item.status !== "ok") {
      btnPreview.disabled = true;
      btnDownload.disabled = true;
    }
    btnPreview.addEventListener("click", (e) => {
      e.stopPropagation();
      selectItem(item.id);
    });
    btnDownload.addEventListener("click", (e) => {
      e.stopPropagation();
      window.location.href = `/api/download/${item.id}`;
    });
    node.addEventListener("click", () => {
      if (item.status === "ok") selectItem(item.id);
    });

    if (state.selectedId === item.id) {
      node.classList.add("selected");
    }
    els.queue.appendChild(node);
  }
}

async function selectItem(id) {
  state.selectedId = id;
  document.querySelectorAll(".item").forEach((n) => {
    n.classList.toggle("selected", n.dataset.id === id);
  });
  const item = state.items.find((x) => x.id === id);
  if (!item) return;
  els.previewTitle.textContent = `미리보기 · ${item.markdownName}`;
  els.preview.textContent = "불러오는 중…";
  try {
    const res = await fetch(`/api/preview/${id}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    els.preview.textContent = data.markdown || "(빈 문서)";
    els.downloadCurrent.disabled = false;
    els.copyMd.disabled = false;
    els.downloadCurrent.onclick = () => {
      window.location.href = `/api/download/${id}`;
    };
    els.copyMd.onclick = async () => {
      try {
        await navigator.clipboard.writeText(data.markdown || "");
        showToast("마크다운을 클립보드에 복사했습니다.", "success");
      } catch {
        showToast("클립보드 복사에 실패했습니다.", "error");
      }
    };
  } catch (err) {
    els.preview.textContent = `미리보기를 불러오지 못했습니다: ${err}`;
  }
}

function validateFiles(files) {
  const cfg = state.config;
  if (!cfg) return { ok: false, error: "설정을 불러오지 못했습니다." };
  if (files.length === 0) return { ok: false, error: "선택된 파일이 없습니다." };
  if (files.length > cfg.maxFilesPerUpload) {
    return { ok: false, error: `한 번에 최대 ${cfg.maxFilesPerUpload}개까지 업로드할 수 있습니다.` };
  }
  const limit = cfg.maxFileSizeMB * 1024 * 1024;
  for (const f of files) {
    if (f.size > limit) {
      return { ok: false, error: `${f.name} 파일이 ${cfg.maxFileSizeMB}MB 제한을 초과했습니다.` };
    }
  }
  return { ok: true };
}

async function uploadFiles(fileList) {
  if (state.uploading) {
    showToast("다른 업로드가 진행 중입니다.", "error");
    return;
  }
  const files = Array.from(fileList || []);
  const check = validateFiles(files);
  if (!check.ok) {
    showToast(check.error, "error");
    return;
  }
  state.uploading = true;
  showToast(`${files.length}개 파일 변환 중…`);

  const form = new FormData();
  for (const f of files) form.append("files", f, f.name);

  try {
    const res = await fetch("/api/convert", { method: "POST", body: form });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    const data = await res.json();
    const okCount = (data.items || []).filter((x) => x.status === "ok").length;
    const errCount = (data.items || []).length - okCount;
    if (errCount === 0) {
      showToast(`${okCount}개 변환 완료`, "success");
    } else {
      showToast(`${okCount}개 성공 · ${errCount}개 실패`, errCount === files.length ? "error" : "info");
    }
    await loadHistory();
    const firstOk = (data.items || []).find((x) => x.status === "ok");
    if (firstOk) selectItem(firstOk.id);
  } catch (err) {
    showToast(`업로드 실패: ${err.message || err}`, "error");
  } finally {
    state.uploading = false;
  }
}

function wire() {
  els.dropzone.addEventListener("click", () => els.fileInput.click());
  els.dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      els.fileInput.click();
    }
  });
  els.fileInput.addEventListener("change", (e) => {
    uploadFiles(e.target.files);
    e.target.value = "";
  });

  ["dragenter", "dragover"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      els.dropzone.classList.add("dragging");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    els.dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (ev === "dragleave" && e.target !== els.dropzone) return;
      els.dropzone.classList.remove("dragging");
    });
  });
  els.dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length) {
      uploadFiles(dt.files);
    }
  });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => e.preventDefault());

  els.refresh.addEventListener("click", () => loadHistory());
  els.downloadAll.addEventListener("click", () => {
    const ids = state.items.filter((i) => i.status === "ok").map((i) => i.id);
    if (ids.length === 0) return;
    window.location.href = `/api/download-zip?ids=${encodeURIComponent(ids.join(","))}`;
  });
}

async function init() {
  wire();
  await loadConfig();
  await loadHistory();
}

init().catch((err) => {
  console.error(err);
  showToast("초기화 실패: " + (err.message || err), "error");
});
