(() => {
  const state = {
    questions: [],
    selectedId: null,
    currentQuestion: null,
    searchTimer: null,
    dueReviews: [],
    knowledgePoints: [],
    questionOffset: 0,
    questionTotal: 0,
    historyOffset: 0,
    historyTotal: 0,
  };

  const statusLabels = {
    draft: "草稿",
    recognized: "已识别",
    corrected: "已校正",
    archived: "已归档",
  };

  const PAGE_SIZE = 20;

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
    questionPreviousButton: $("questionPreviousButton"),
    questionNextButton: $("questionNextButton"),
    questionPageText: $("questionPageText"),
    libraryTotalCount: $("libraryTotalCount"),
    libraryStatsStatus: $("libraryStatsStatus"),
    libraryStatusStats: $("libraryStatusStats"),
    librarySubjectStats: $("librarySubjectStats"),
    libraryKnowledgeStats: $("libraryKnowledgeStats"),
    reviewHistoryCount: $("reviewHistoryCount"),
    reviewHistoryResultFilter: $("reviewHistoryResultFilter"),
    reviewHistoryFromInput: $("reviewHistoryFromInput"),
    reviewHistoryToInput: $("reviewHistoryToInput"),
    reviewHistoryFilterButton: $("reviewHistoryFilterButton"),
    reviewHistoryStatus: $("reviewHistoryStatus"),
    reviewHistoryList: $("reviewHistoryList"),
    reviewHistoryPreviousButton: $("reviewHistoryPreviousButton"),
    reviewHistoryNextButton: $("reviewHistoryNextButton"),
    reviewHistoryPageText: $("reviewHistoryPageText"),
    dueReviewCount: $("dueReviewCount"),
    dueReviewStatus: $("dueReviewStatus"),
    dueReviewList: $("dueReviewList"),
    reviewStatsStatus: $("reviewStatsStatus"),
    statsDueCount: $("statsDueCount"),
    statsTodayCount: $("statsTodayCount"),
    statsWeekCount: $("statsWeekCount"),
    statsMasteredRate: $("statsMasteredRate"),
    statsResultSummary: $("statsResultSummary"),
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
    knowledgePointList: $("knowledgePointList"),
    knowledgePointNameInput: $("knowledgePointNameInput"),
    knowledgePointSubjectInput: $("knowledgePointSubjectInput"),
    createKnowledgePointButton: $("createKnowledgePointButton"),
    knowledgePointState: $("knowledgePointState"),
    mistakeTagsInput: $("mistakeTagsInput"),
    mistakeTagSuggestions: $("mistakeTagSuggestions"),
    nextReviewText: $("nextReviewText"),
    scheduleReviewControls: $("scheduleReviewControls"),
    reviewDueAtInput: $("reviewDueAtInput"),
    scheduleReviewButton: $("scheduleReviewButton"),
    reviewScheduleState: $("reviewScheduleState"),
    exportJsonButton: $("exportJsonButton"),
    exportMarkdownButton: $("exportMarkdownButton"),
    archiveQuestionButton: $("archiveQuestionButton"),
    restoreQuestionButton: $("restoreQuestionButton"),
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

  function parseMistakeTags(value) {
    const seen = new Set();
    return value.split(/[,，]/).map((name) => name.trim()).filter((name) => {
      const key = name.toLocaleLowerCase();
      if (!name || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function nextReviewDate(result) {
    const intervals = {
      again: 10 * 60 * 1000,
      hard: 24 * 60 * 60 * 1000,
      good: 3 * 24 * 60 * 60 * 1000,
      easy: 7 * 24 * 60 * 60 * 1000,
    };
    return new Date(Date.now() + intervals[result]).toISOString();
  }

  function latestJob(question) {
    const jobs = question.ocr_jobs || [];
    return jobs.length ? jobs[jobs.length - 1] : question.latest_ocr_job;
  }

  function assetUrl(asset) {
    return `/api/assets/${asset.asset_id}/file`;
  }

  function renderCompactStats(container, items, emptyText = "暂无数据") {
    container.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("span");
      empty.textContent = emptyText;
      container.append(empty);
      return;
    }
    items.forEach(({ label, value }) => {
      const row = document.createElement("div");
      const name = document.createElement("span");
      name.textContent = label;
      const count = document.createElement("strong");
      count.textContent = String(value);
      row.append(name, count);
      container.append(row);
    });
  }

  async function loadQuestionStats() {
    setStateText(elements.libraryStatsStatus, "统计中...");
    try {
      const stats = await requestJSON("/api/questions/stats?knowledge_limit=8");
      elements.libraryTotalCount.textContent = `${stats.total_questions || 0} 题`;
      renderCompactStats(
        elements.libraryStatusStats,
        Object.entries(stats.status_counts || {}).map(([status, count]) => ({
          label: statusLabels[status] || status,
          value: count,
        })),
      );
      renderCompactStats(
        elements.librarySubjectStats,
        (stats.subject_counts || []).map((item) => ({ label: item.subject === "Uncategorized" ? "未分科" : item.subject, value: item.question_count })),
      );
      renderCompactStats(
        elements.libraryKnowledgeStats,
        (stats.top_knowledge_points || []).map((item) => ({
          label: item.subject ? `${item.subject} · ${item.name}` : item.name,
          value: item.question_count,
        })),
      );
      setStateText(elements.libraryStatsStatus, "已更新", "success");
    } catch (error) {
      setStateText(elements.libraryStatsStatus, error.message, "error");
    }
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
      const tags = (question.mistake_tags || []).slice(0, 3);
      if (tags.length) {
        const tagRow = document.createElement("div");
        tagRow.className = "tag-row";
        tags.forEach((tag) => {
          const chip = document.createElement("span");
          chip.className = "tag-chip";
          chip.textContent = tag.name;
          tagRow.append(chip);
        });
        body.append(tagRow);
      }
      item.append(thumb, body);
      elements.questionList.append(item);
    }
  }

  function renderDueReviews() {
    elements.dueReviewList.replaceChildren();
    elements.dueReviewCount.textContent = `${state.dueReviews.length} 条`;
    if (!state.dueReviews.length) {
      const empty = document.createElement("p");
      empty.className = "empty-review";
      empty.textContent = "当前没有到期复习。";
      elements.dueReviewList.append(empty);
      return;
    }
    for (const review of state.dueReviews) {
      const question = review.question;
      const card = document.createElement("article");
      card.className = "review-card";
      const image = document.createElement("img");
      image.alt = "";
      image.className = "review-thumb";
      if (question.first_asset) image.src = assetUrl(question.first_asset);
      const body = document.createElement("div");
      const title = document.createElement("h3");
      title.textContent = questionTitle(question);
      const meta = document.createElement("p");
      meta.className = "question-meta";
      meta.textContent = `${question.subject || "未分科"} · 到期 ${formatDate(review.due_at)}`;
      const preview = document.createElement("p");
      preview.className = "question-preview";
      preview.textContent = textSnippet(question.corrected_text || question.raw_text, "暂无文本");
      const actions = document.createElement("div");
      actions.className = "review-actions";
      [["again", "再来一次"], ["hard", "困难"], ["good", "掌握"], ["easy", "简单"]].forEach(([result, label]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "review-result-button";
        button.dataset.reviewId = String(review.review_id);
        button.dataset.result = result;
        button.textContent = label;
        actions.append(button);
      });
      body.append(title, meta, preview, actions);
      card.append(image, body);
      elements.dueReviewList.append(card);
    }
  }

  function reviewResultLabel(result) {
    return { again: "再来一次", hard: "困难", good: "掌握", easy: "简单" }[result] || result || "未知";
  }

  function renderReviewHistory(items) {
    elements.reviewHistoryList.replaceChildren();
    elements.reviewHistoryCount.textContent = `${items.length} 条`;
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-review";
      empty.textContent = "暂无匹配的复习记录。";
      elements.reviewHistoryList.append(empty);
      return;
    }
    for (const review of items) {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "history-item";
      row.dataset.questionId = String(review.question_id);
      const title = document.createElement("strong");
      title.textContent = questionTitle(review.question);
      const meta = document.createElement("span");
      meta.textContent = `${reviewResultLabel(review.result)} · ${formatDate(review.reviewed_at)} · ${review.question.subject || "未分科"}`;
      row.append(title, meta);
      elements.reviewHistoryList.append(row);
    }
  }

  async function loadReviewHistory() {
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(state.historyOffset) });
    if (elements.reviewHistoryResultFilter.value) params.set("result", elements.reviewHistoryResultFilter.value);
    if (elements.reviewHistoryFromInput.value) params.set("reviewed_from", `${elements.reviewHistoryFromInput.value}T00:00:00`);
    if (elements.reviewHistoryToInput.value) params.set("reviewed_to", `${elements.reviewHistoryToInput.value}T23:59:59`);
    setStateText(elements.reviewHistoryStatus, "加载中...");
    try {
      const data = await requestJSON(`/api/reviews/history?${params.toString()}`);
      renderReviewHistory(data.items || []);
      state.historyTotal = data.total || 0;
      elements.reviewHistoryCount.textContent = `${state.historyTotal} 条`;
      const historyPage = Math.floor(state.historyOffset / PAGE_SIZE) + 1;
      const historyPages = Math.max(1, Math.ceil(state.historyTotal / PAGE_SIZE));
      elements.reviewHistoryPageText.textContent = `第 ${historyPage} / ${historyPages} 页`;
      elements.reviewHistoryPreviousButton.disabled = state.historyOffset === 0;
      elements.reviewHistoryNextButton.disabled = state.historyOffset + PAGE_SIZE >= state.historyTotal;
      setStateText(elements.reviewHistoryStatus, "已更新", "success");
    } catch (error) {
      setStateText(elements.reviewHistoryStatus, error.message, "error");
    }
  }

  async function loadReviewStats() {
    setStateText(elements.reviewStatsStatus, "统计中...");
    try {
      const stats = await requestJSON("/api/reviews/stats");
      const counts = stats.result_counts_seven_days || {};
      elements.statsDueCount.textContent = String(stats.due_count || 0);
      elements.statsTodayCount.textContent = String(stats.completed_today || 0);
      elements.statsWeekCount.textContent = String(stats.completed_seven_days || 0);
      elements.statsMasteredRate.textContent = stats.mastered_rate_seven_days === null
        ? "--"
        : `${Math.round(stats.mastered_rate_seven_days * 100)}%`;
      elements.statsResultSummary.textContent = ["again", "hard", "good", "easy"]
        .map((result) => counts[result] || 0)
        .join(" / ");
      setStateText(elements.reviewStatsStatus, "已更新", "success");
    } catch (error) {
      setStateText(elements.reviewStatsStatus, error.message, "error");
    }
  }

  async function loadDueReviews() {
    setStateText(elements.dueReviewStatus, "加载中...");
    try {
      const data = await requestJSON("/api/reviews/due?limit=50");
      state.dueReviews = data.items || [];
      renderDueReviews();
      setStateText(elements.dueReviewStatus, state.dueReviews.length ? "待复习" : "已完成", "success");
    } catch (error) {
      setStateText(elements.dueReviewStatus, error.message, "error");
    }
  }

  function selectedKnowledgePointIds() {
    return Array.from(elements.knowledgePointList.querySelectorAll("input:checked"), (input) => Number(input.value));
  }

  function renderKnowledgePoints(selectedIds = []) {
    const selected = new Set(selectedIds);
    elements.knowledgePointList.replaceChildren();
    if (!state.knowledgePoints.length) {
      const empty = document.createElement("small");
      empty.textContent = "暂无知识点，可在下方新建。";
      elements.knowledgePointList.append(empty);
      return;
    }
    for (const point of state.knowledgePoints) {
      const label = document.createElement("label");
      label.className = "knowledge-point-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = String(point.knowledge_point_id);
      checkbox.checked = selected.has(point.knowledge_point_id);
      const text = document.createElement("span");
      text.textContent = point.subject ? `${point.subject} · ${point.name}` : point.name;
      label.append(checkbox, text);
      elements.knowledgePointList.append(label);
    }
  }

  async function loadKnowledgePoints(selectedIds = null) {
    try {
      const data = await requestJSON("/api/knowledge-points?limit=200");
      state.knowledgePoints = data.items || [];
      const currentIds = selectedIds || (state.currentQuestion?.knowledge_points || []).map((point) => point.knowledge_point_id);
      renderKnowledgePoints(currentIds);
      setStateText(elements.knowledgePointState, "");
    } catch (error) {
      setStateText(elements.knowledgePointState, error.message, "error");
    }
  }

  async function handleCreateKnowledgePoint() {
    const name = elements.knowledgePointNameInput.value.trim();
    if (!name) {
      setStateText(elements.knowledgePointState, "请输入知识点名称", "error");
      return;
    }
    const selectedIds = selectedKnowledgePointIds();
    elements.createKnowledgePointButton.disabled = true;
    try {
      const data = await requestJSON("/api/knowledge-points", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          subject: cleanValue(elements.knowledgePointSubjectInput.value) || cleanValue(elements.subjectInput.value),
        }),
      });
      selectedIds.push(data.knowledge_point.knowledge_point_id);
      elements.knowledgePointNameInput.value = "";
      await loadKnowledgePoints(selectedIds);
      markDirty();
      setStateText(elements.knowledgePointState, "已创建并选中", "success");
    } catch (error) {
      setStateText(elements.knowledgePointState, error.message, "error");
    } finally {
      elements.createKnowledgePointButton.disabled = false;
    }
  }

  async function loadMistakeTagSuggestions() {
    try {
      const data = await requestJSON("/api/mistake-tags?limit=100");
      elements.mistakeTagSuggestions.replaceChildren();
      (data.items || []).forEach((tag) => {
        const option = document.createElement("option");
        option.value = tag.name;
        elements.mistakeTagSuggestions.append(option);
      });
    } catch {
      elements.mistakeTagSuggestions.replaceChildren();
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
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(state.questionOffset) });
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
      state.questionTotal = data.total || 0;
      renderQuestionList(state.questionTotal);
      const questionPage = Math.floor(state.questionOffset / PAGE_SIZE) + 1;
      const questionPages = Math.max(1, Math.ceil(state.questionTotal / PAGE_SIZE));
      elements.questionPageText.textContent = `第 ${questionPage} / ${questionPages} 页`;
      elements.questionPreviousButton.disabled = state.questionOffset === 0;
      elements.questionNextButton.disabled = state.questionOffset + PAGE_SIZE >= state.questionTotal;
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
    elements.archiveQuestionButton.hidden = question.status === "archived";
    elements.restoreQuestionButton.hidden = question.status !== "archived";
    elements.rawTextInput.value = question.raw_text || "";
    elements.correctedTextInput.value = question.corrected_text || "";
    renderKnowledgePoints((question.knowledge_points || []).map((point) => point.knowledge_point_id));
    elements.knowledgePointSubjectInput.value = question.subject || "";
    elements.mistakeTagsInput.value = (question.mistake_tags || []).map((tag) => tag.name).join(", ");
    elements.nextReviewText.textContent = question.next_review ? formatDate(question.next_review.due_at) : "尚未安排";
    elements.scheduleReviewControls.hidden = Boolean(question.next_review);
    elements.reviewDueAtInput.value = "";
    setStateText(elements.reviewScheduleState, question.next_review ? "已有待完成计划" : "");
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
      if (!state.knowledgePoints.length) {
        await loadKnowledgePoints(
          (data.question.knowledge_points || []).map((point) => point.knowledge_point_id),
        );
      }
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
      await requestJSON(`/api/questions/${question.question_id}/knowledge-points`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: selectedKnowledgePointIds() }),
      });
      await requestJSON(`/api/questions/${question.question_id}/mistake-tags`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names: parseMistakeTags(elements.mistakeTagsInput.value) }),
      });
      const refreshed = await requestJSON(`/api/questions/${question.question_id}`);
      state.currentQuestion = refreshed.question;
      renderDetail(refreshed.question);
      setStateText(elements.saveState, "已保存", "success");
      await loadQuestions();
      await loadMistakeTagSuggestions();
    } catch (error) {
      setStateText(elements.saveState, error.message, "error");
    } finally {
      elements.saveButton.disabled = false;
    }
  }

  function downloadQuestionExport(format) {
    const question = state.currentQuestion;
    if (!question) return;
    window.location.assign(`/api/questions/${question.question_id}/export?format=${format}`);
  }

  async function handleArchiveAction(action) {
    const question = state.currentQuestion;
    if (!question) return;
    const button = action === "archive" ? elements.archiveQuestionButton : elements.restoreQuestionButton;
    button.disabled = true;
    try {
      const data = await requestJSON(`/api/questions/${question.question_id}/${action}`, { method: "POST" });
      state.currentQuestion = data.question;
      renderDetail(data.question);
      await loadQuestions();
      await loadQuestionStats();
      setStateText(elements.saveState, action === "archive" ? "已归档" : "已恢复", "success");
    } catch (error) {
      setStateText(elements.saveState, error.message, "error");
    } finally {
      button.disabled = false;
    }
  }

  async function handleScheduleReview() {
    const question = state.currentQuestion;
    const dueAt = elements.reviewDueAtInput.value;
    if (!question || !dueAt) {
      setStateText(elements.reviewScheduleState, "请选择复习时间", "error");
      return;
    }
    elements.scheduleReviewButton.disabled = true;
    try {
      await requestJSON(`/api/questions/${question.question_id}/reviews`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ due_at: new Date(dueAt).toISOString() }),
      });
      await selectQuestion(question.question_id);
      await loadQuestions();
      await loadDueReviews();
      setStateText(elements.reviewScheduleState, "已安排", "success");
    } catch (error) {
      setStateText(elements.reviewScheduleState, error.message, "error");
    } finally {
      elements.scheduleReviewButton.disabled = false;
    }
  }

  async function handleReviewResult(event) {
    const target = event.target instanceof Element ? event.target.closest("[data-review-id]") : null;
    if (!target) return;
    target.disabled = true;
    try {
      await requestJSON(`/api/reviews/${target.dataset.reviewId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result: target.dataset.result, next_due_at: nextReviewDate(target.dataset.result) }),
      });
      await loadDueReviews();
      await loadQuestions();
      if (state.selectedId) await selectQuestion(state.selectedId);
    } catch (error) {
      setStateText(elements.dueReviewStatus, error.message, "error");
      target.disabled = false;
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
    elements.refreshButton.addEventListener("click", () => { loadQuestions(); loadQuestionStats(); loadDueReviews(); loadReviewStats(); });
    elements.scheduleReviewButton.addEventListener("click", handleScheduleReview);
    elements.exportJsonButton.addEventListener("click", () => downloadQuestionExport("json"));
    elements.exportMarkdownButton.addEventListener("click", () => downloadQuestionExport("markdown"));
    elements.archiveQuestionButton.addEventListener("click", () => handleArchiveAction("archive"));
    elements.restoreQuestionButton.addEventListener("click", () => handleArchiveAction("restore"));
    elements.reviewHistoryFilterButton.addEventListener("click", () => { state.historyOffset = 0; loadReviewHistory(); });
    elements.reviewHistoryPreviousButton.addEventListener("click", () => { state.historyOffset = Math.max(0, state.historyOffset - PAGE_SIZE); loadReviewHistory(); });
    elements.reviewHistoryNextButton.addEventListener("click", () => { state.historyOffset += PAGE_SIZE; loadReviewHistory(); });
    elements.questionPreviousButton.addEventListener("click", () => { state.questionOffset = Math.max(0, state.questionOffset - PAGE_SIZE); loadQuestions(); });
    elements.questionNextButton.addEventListener("click", () => { state.questionOffset += PAGE_SIZE; loadQuestions(); });
    elements.reviewHistoryList.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target.closest("[data-question-id]") : null;
      if (target) selectQuestion(Number(target.dataset.questionId));
    });
    elements.createKnowledgePointButton.addEventListener("click", handleCreateKnowledgePoint);
    elements.knowledgePointList.addEventListener("change", markDirty);
    elements.dueReviewList.addEventListener("click", handleReviewResult);

    elements.questionList.addEventListener("click", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      const item = target ? target.closest(".question-item") : null;
      if (item) {
        selectQuestion(Number(item.dataset.id));
      }
    });

    elements.searchInput.addEventListener("input", () => {
      window.clearTimeout(state.searchTimer);
      state.questionOffset = 0;
      state.searchTimer = window.setTimeout(() => loadQuestions(), 250);
    });

    elements.statusFilter.addEventListener("change", () => { state.questionOffset = 0; loadQuestions(); });

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
      elements.mistakeTagsInput,
    ].forEach((element) => element.addEventListener("input", markDirty));
  }

  function setupKeyboardShortcuts() {
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const editing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && state.currentQuestion) {
        event.preventDefault();
        elements.detailForm.requestSubmit();
        return;
      }
      if (!editing && event.key === "/") {
        event.preventDefault();
        elements.searchInput.focus();
      }
      if (!editing && event.key.toLowerCase() === "r") {
        event.preventDefault();
        elements.refreshButton.click();
      }
    });
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
  loadQuestionStats();
  loadReviewHistory();
  loadDueReviews();
  loadReviewStats();
  loadKnowledgePoints();
  loadMistakeTagSuggestions();
})();
