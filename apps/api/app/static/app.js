(() => {
  const state = {
    questions: [],
    selectedId: null,
    currentQuestion: null,
    searchTimer: null,
  };

  const statusLabels = {
    draft: "草稿",
    recognized: "已识别",
    corrected: "已校正",
    archived: "已归档",
  };

  const jobLabels = {
    pending: "等待 OCR",
    running: "OCR 进行中",
    succeeded: "OCR 已完成",
    failed: "OCR 失败",
  };

  const $ = (id) => document.getElementById(id);

  const elements = {
    uploadForm: $("uploadForm"),
    imageInput: $("imageInput"),
    uploadButton: $("uploadButton"),
    uploadState: $("uploadState"),
    refreshButton: $("refreshButton"),
    searchInput: $("searchInput"),
    statusFilter: $("statusFilter"),
    listCount: $("listCount"),
    listStatus: $("listStatus"),
    questionList: $("questionList"),
    emptyDetail: $("emptyDetail"),
    detailForm: $("detailForm"),
    detailId: $("detailId"),
    detailHeading: $("detailHeading"),
    detailStatus: $("detailStatus"),
    questionImage: $("questionImage"),
    titleInput: $("titleInput"),
    subjectInput: $("subjectInput"),
    typeInput: $("typeInput"),
    difficultyInput: $("difficultyInput"),
    questionStatusInput: $("questionStatusInput"),
    rawTextInput: $("rawTextInput"),
    correctedTextInput: $("correctedTextInput"),
    saveButton: $("saveButton"),
    copyRawButton: $("copyRawButton"),
    saveState: $("saveState"),
    fileLabel: document.querySelector(".file-picker span"),
  };

  function setStateText(element, message, type = "") {
    element.textContent = message;
    element.classList.toggle("is-error", type === "error");
    element.classList.toggle("is-success", type === "success");
  }

  async function requestJSON(path, options = {}) {
    const headers = {
      Accept: "application/json",
      ...(options.headers || {}),
    };
    const response = await fetch(path, { ...options, headers });
    if (!response.ok) {
      let message = `${response.status} ${response.statusText}`;
      try {
        const errorBody = await response.json();
        message = errorBody.detail || message;
      } catch {
        // Keep the HTTP status text when the server returns a non-JSON error.
      }
      throw new Error(message);
    }
    return response.status === 204 ? {} : response.json();
  }

  function cleanValue(value) {
    const trimmed = value.trim();
    return trimmed || null;
  }

  function textSnippet(value, fallback = "") {
    if (!value) {
      return fallback;
    }
    const compact = value.replace(/\s+/g, " ").trim();
    return compact.length > 90 ? `${compact.slice(0, 90)}...` : compact;
  }

  function questionTitle(question) {
    return (
      question.title ||
      textSnippet(question.corrected_text) ||
      textSnippet(question.raw_text) ||
      `错题 #${question.question_id}`
    );
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function latestJob(question) {
    const jobs = question.ocr_jobs || [];
    return jobs.length ? jobs[jobs.length - 1] : question.latest_ocr_job;
  }

  function assetUrl(asset) {
    return `/api/assets/${asset.asset_id}/file`;
  }

  function renderQuestionList(total) {
    elements.questionList.replaceChildren();
    elements.listCount.textContent = `${total} 条`;

    if (!state.questions.length) {
      const empty = document.createElement("div");
      empty.className = "empty-list";
      empty.textContent = "暂无错题";
      elements.questionList.append(empty);
      return;
    }

    for (const question of state.questions) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "question-item";
      item.dataset.id = String(question.question_id);
      item.setAttribute("role", "listitem");
      item.classList.toggle("is-selected", question.question_id === state.selectedId);

      const thumb = document.createElement("img");
      thumb.className = "question-thumb";
      thumb.alt = "";
      if (question.first_asset) {
        thumb.src = assetUrl(question.first_asset);
      }

      const body = document.createElement("div");
      const title = document.createElement("p");
      title.className = "question-title";
      title.textContent = questionTitle(question);

      const meta = document.createElement("p");
      meta.className = "question-meta";
      meta.textContent = `#${question.question_id} · ${question.subject || "未分科"} · ${formatDate(question.updated_at)}`;

      const preview = document.createElement("p");
      preview.className = "question-preview";
      const job = latestJob(question);
      preview.textContent = textSnippet(
        question.corrected_text || question.raw_text,
        job ? jobLabels[job.status] || job.status : "等待 OCR",
      );

      const pill = document.createElement("span");
      pill.className = `status-pill ${question.status || ""}`;
      pill.textContent = statusLabels[question.status] || question.status || "未知";

      body.append(title, meta, preview, pill);
      item.append(thumb, body);
      elements.questionList.append(item);
    }
  }

  function showEmptyDetail() {
    state.currentQuestion = null;
    state.selectedId = null;
    elements.detailForm.hidden = true;
    elements.emptyDetail.hidden = false;
  }

  function renderListSelection() {
    document.querySelectorAll(".question-item").forEach((item) => {
      item.classList.toggle("is-selected", Number(item.dataset.id) === state.selectedId);
    });
  }

  async function loadQuestions({ selectFirst = false } = {}) {
    const params = new URLSearchParams({ limit: "50" });
    const query = elements.searchInput.value.trim();
    const status = elements.statusFilter.value;
    if (query) {
      params.set("q", query);
    }
    if (status) {
      params.set("status", status);
    }

    setStateText(elements.listStatus, "加载中...");
    try {
      const data = await requestJSON(`/api/questions?${params.toString()}`);
      state.questions = data.items || [];
      renderQuestionList(data.total || 0);
      setStateText(elements.listStatus, state.questions.length ? "已更新" : "没有匹配结果", state.questions.length ? "success" : "");

      const selectedStillVisible = state.questions.some((question) => question.question_id === state.selectedId);
      if (selectFirst && !state.selectedId && state.questions.length) {
        await selectQuestion(state.questions[0].question_id);
      } else if (state.selectedId && !selectedStillVisible) {
        showEmptyDetail();
      } else {
        renderListSelection();
      }
    } catch (error) {
      setStateText(elements.listStatus, error.message, "error");
    }
  }

  function renderDetail(question) {
    const firstAsset = (question.assets || [])[0] || question.first_asset;
    const job = latestJob(question);

    elements.emptyDetail.hidden = true;
    elements.detailForm.hidden = false;
    elements.detailId.textContent = `Question #${question.question_id}`;
    elements.detailHeading.textContent = questionTitle(question);
    elements.titleInput.value = question.title || "";
    elements.subjectInput.value = question.subject || "";
    elements.typeInput.value = question.question_type || "";
    elements.difficultyInput.value = question.difficulty || "";
    elements.questionStatusInput.value = question.status || "draft";
    elements.rawTextInput.value = question.raw_text || "";
    elements.correctedTextInput.value = question.corrected_text || "";
    if (firstAsset) {
      elements.questionImage.src = assetUrl(firstAsset);
      elements.questionImage.hidden = false;
    } else {
      elements.questionImage.removeAttribute("src");
      elements.questionImage.hidden = true;
    }

    const jobText = job ? jobLabels[job.status] || job.status : "暂无 OCR 任务";
    const confidence = job && job.confidence ? ` · 置信度 ${Math.round(job.confidence * 100)}%` : "";
    setStateText(elements.detailStatus, `${statusLabels[question.status] || question.status || "未知"} · ${jobText}${confidence}`);
    setStateText(elements.saveState, "未修改");
  }

  async function selectQuestion(questionId) {
    state.selectedId = questionId;
    renderListSelection();
    setStateText(elements.detailStatus, "加载详情...");
    try {
      const data = await requestJSON(`/api/questions/${questionId}`);
      state.currentQuestion = data.question;
      renderDetail(data.question);
    } catch (error) {
      setStateText(elements.detailStatus, error.message, "error");
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    const file = elements.imageInput.files[0];
    if (!file) {
      setStateText(elements.uploadState, "请选择图片", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    elements.uploadButton.disabled = true;
    setStateText(elements.uploadState, "上传中...");

    try {
      const upload = await requestJSON("/api/questions/upload", {
        method: "POST",
        body: formData,
      });
      elements.statusFilter.value = "";
      elements.uploadForm.reset();
      elements.fileLabel.textContent = "拍照或选择图片";
      setStateText(elements.uploadState, `已上传，OCR 任务 #${upload.ocr_job_id}`, "success");
      await loadQuestions();
      await selectQuestion(upload.question_id);
    } catch (error) {
      setStateText(elements.uploadState, error.message, "error");
    } finally {
      elements.uploadButton.disabled = false;
    }
  }

  async function handleSave(event) {
    event.preventDefault();
    const question = state.currentQuestion;
    if (!question) {
      return;
    }

    const payload = {
      title: cleanValue(elements.titleInput.value),
      subject: cleanValue(elements.subjectInput.value),
      question_type: cleanValue(elements.typeInput.value),
      difficulty: cleanValue(elements.difficultyInput.value),
      status: elements.questionStatusInput.value,
      corrected_text: cleanValue(elements.correctedTextInput.value),
    };

    elements.saveButton.disabled = true;
    setStateText(elements.saveState, "保存中...");
    try {
      const data = await requestJSON(`/api/questions/${question.question_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.currentQuestion = data.question;
      renderDetail(data.question);
      setStateText(elements.saveState, "已保存", "success");
      await loadQuestions();
    } catch (error) {
      setStateText(elements.saveState, error.message, "error");
    } finally {
      elements.saveButton.disabled = false;
    }
  }

  function markDirty() {
    if (state.currentQuestion) {
      setStateText(elements.saveState, "有未保存修改");
    }
  }

  function setupEvents() {
    elements.uploadForm.addEventListener("submit", handleUpload);
    elements.detailForm.addEventListener("submit", handleSave);
    elements.refreshButton.addEventListener("click", () => loadQuestions());

    elements.questionList.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      const item = target ? target.closest(".question-item") : null;
      if (item) {
        selectQuestion(Number(item.dataset.id));
      }
    });

    elements.searchInput.addEventListener("input", () => {
      window.clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(() => loadQuestions(), 250);
    });

    elements.statusFilter.addEventListener("change", () => loadQuestions());

    elements.imageInput.addEventListener("change", () => {
      const file = elements.imageInput.files[0];
      elements.fileLabel.textContent = file ? file.name : "拍照或选择图片";
      setStateText(elements.uploadState, file ? "图片已选择" : "等待图片");
    });

    elements.copyRawButton.addEventListener("click", () => {
      elements.correctedTextInput.value = elements.rawTextInput.value;
      markDirty();
    });

    [
      elements.titleInput,
      elements.subjectInput,
      elements.typeInput,
      elements.difficultyInput,
      elements.questionStatusInput,
      elements.correctedTextInput,
    ].forEach((element) => element.addEventListener("input", markDirty));
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) {
      return;
    }
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/app/service-worker.js").catch(() => {});
    });
  }

  setupEvents();
  registerServiceWorker();
  loadQuestions({ selectFirst: true });
})();
