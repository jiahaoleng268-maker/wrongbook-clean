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
    selectedImageFiles: [],
    activeView: "library",
    formulaSelection: null,
    formulaImage: null,
    sources: [],
    sourceFilterId: null,
    chapterFilterId: null,
    selectedQuestionIds: new Set(),
    smartFilter: "",
    questionView: "card",
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
    cameraInput: $("cameraInput"),
    galleryInput: $("galleryInput"),
    selectedImageName: $("selectedImageName"),
    uploadButton: $("uploadButton"),
    uploadState: $("uploadState"),
    manualTitleInput: $("manualTitleInput"),
    manualSubjectInput: $("manualSubjectInput"),
    manualSourceInput: $("manualSourceInput"),
    manualTypeInput: $("manualTypeInput"),
    paddleTextInput: $("paddleTextInput"),
    manualSourceSelect: $("manualSourceSelect"),
    manualChapterSelect: $("manualChapterSelect"),
    manualSourcePageInput: $("manualSourcePageInput"),
    refreshButton: $("refreshButton"),
    searchInput: $("searchInput"),
    statusFilter: $("statusFilter"),
    exportFilteredJsonButton: $("exportFilteredJsonButton"),
    exportFilteredMarkdownButton: $("exportFilteredMarkdownButton"),
    questionImportInput: $("questionImportInput"),
    questionImportFileLabel: $("questionImportFileLabel"),
    importQuestionsButton: $("importQuestionsButton"),
    questionImportState: $("questionImportState"),
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
    rerunOcrButton: $("rerunOcrButton"),
    openFormulaCropButton: $("openFormulaCropButton"),
    formulaHistoryList: $("formulaHistoryList"),
    formulaHistoryState: $("formulaHistoryState"),
    formulaCropDialog: $("formulaCropDialog"),
    formulaCropCanvas: $("formulaCropCanvas"),
    closeFormulaCropButton: $("closeFormulaCropButton"),
    submitFormulaCropButton: $("submitFormulaCropButton"),
    formulaCropState: $("formulaCropState"),
    saveState: $("saveState"),
    answerTextInput: $("answerTextInput"),
    solutionTextInput: $("solutionTextInput"),
    personalSolutionInput: $("personalSolutionInput"),
    keyStepsInput: $("keyStepsInput"),
    wrongAnswerInput: $("wrongAnswerInput"),
    mistakeAnalysisInput: $("mistakeAnalysisInput"),
    notesInput: $("notesInput"),
    sourceSelect: $("sourceSelect"),
    chapterSelect: $("chapterSelect"),
    sourcePageInput: $("sourcePageInput"),
    latexPreviewContent: $("latexPreviewContent"),
    sourceTree: $("sourceTree"),
    openSourceDialogButton: $("openSourceDialogButton"),
    sourceDialog: $("sourceDialog"),
    closeSourceDialogButton: $("closeSourceDialogButton"),
    sourceForm: $("sourceForm"),
    sourceNameInput: $("sourceNameInput"),
    sourceSubjectInput: $("sourceSubjectInput"),
    sourceTypeInput: $("sourceTypeInput"),
    chapterForm: $("chapterForm"),
    chapterSourceInput: $("chapterSourceInput"),
    parentChapterInput: $("parentChapterInput"),
    chapterNameInput: $("chapterNameInput"),
    sourceDialogState: $("sourceDialogState"),
    selectPageQuestions: $("selectPageQuestions"),
    bulkSourceSelect: $("bulkSourceSelect"),
    bulkChapterSelect: $("bulkChapterSelect"),
    bulkStatusSelect: $("bulkStatusSelect"),
    applyBulkButton: $("applyBulkButton"),
    bulkState: $("bulkState"),
    smartFolders: $("smartFolders"),
    cardViewButton: $("cardViewButton"),
    tableViewButton: $("tableViewButton"),
    answerPreview: $("answerPreview"),
    solutionPreview: $("solutionPreview"),
    assetGallery: $("assetGallery"),
    assetState: $("assetState"),
    newAssetType: $("newAssetType"),
    newAssetInput: $("newAssetInput"),
    uploadAssetsButton: $("uploadAssetsButton"),
    assetPreviewDialog: $("assetPreviewDialog"),
    assetPreviewImage: $("assetPreviewImage"),
    closeAssetPreviewButton: $("closeAssetPreviewButton"),
    detailTabs: Array.from(document.querySelectorAll("[data-detail-tab]")),
    detailPanels: Array.from(document.querySelectorAll("[data-detail-panel]")),
    appViews: Array.from(document.querySelectorAll(".app-view")),
    bottomNavItems: Array.from(document.querySelectorAll(".bottom-nav-item")),
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
    elements.questionList.classList.toggle("is-table-view", state.questionView === "table");
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

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "question-select";
      checkbox.checked = state.selectedQuestionIds.has(question.question_id);
      checkbox.addEventListener("click", (event) => event.stopPropagation());
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.selectedQuestionIds.add(question.question_id); else state.selectedQuestionIds.delete(question.question_id);
      });

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
      item.append(checkbox, thumb, body);
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

  const assetTypeLabels = { original: "原图", question_image: "题目图", answer_image: "答案图", solution_image: "解析图", draft_image: "草稿图", source_page: "原始页", attachment: "附件", formula_crop: "公式裁剪" };

  function renderAssetGallery(question) {
    elements.assetGallery.replaceChildren();
    const assets = question.assets || [];
    if (!assets.length) { elements.assetGallery.textContent = "暂无附件"; return; }
    assets.forEach((asset) => {
      const card = document.createElement("article"); card.className = "asset-card";
      const image = document.createElement("img"); image.src = assetUrl(asset); image.alt = assetTypeLabels[asset.asset_type] || asset.asset_type;
      image.addEventListener("click", () => { elements.assetPreviewImage.src = image.src; elements.assetPreviewDialog.showModal(); });
      const select = document.createElement("select");
      Object.entries(assetTypeLabels).filter(([value]) => value !== "formula_crop").forEach(([value, label]) => { const option = document.createElement("option"); option.value = value; option.textContent = label; select.append(option); });
      select.value = asset.asset_type;
      select.addEventListener("change", async () => { try { await requestJSON(`/api/assets/${asset.asset_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_type: select.value }) }); setStateText(elements.assetState, "附件类型已更新", "success"); } catch (error) { setStateText(elements.assetState, error.message, "error"); } });
      const remove = document.createElement("button"); remove.type = "button"; remove.className = "danger-button"; remove.textContent = "删除";
      remove.addEventListener("click", async () => { if (!window.confirm("确定删除这张附件图片？")) return; try { await requestJSON(`/api/assets/${asset.asset_id}`, { method: "DELETE" }); await selectQuestion(question.question_id); setStateText(elements.assetState, "附件已删除", "success"); } catch (error) { setStateText(elements.assetState, error.message, "error"); } });
      card.append(image, select, remove); elements.assetGallery.append(card);
    });
  }

  function orderedChapters(chapters) {
    const byParent = new Map();
    chapters.forEach((chapter) => { const key = chapter.parent_id || 0; if (!byParent.has(key)) byParent.set(key, []); byParent.get(key).push(chapter); });
    byParent.forEach((items) => items.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name)));
    const result = [];
    function visit(parentId, depth) { (byParent.get(parentId) || []).forEach((chapter) => { result.push({ chapter, depth }); visit(chapter.chapter_id, depth + 1); }); }
    visit(0, 0); return result;
  }
  function renderFormulaHistory(question) {
    const jobs = (question.ocr_jobs || []).filter((job) => job.engine_name === "formula").reverse();
    elements.formulaHistoryList.replaceChildren();
    if (!jobs.length) {
      setStateText(elements.formulaHistoryState, "暂无公式识别");
      return;
    }
    setStateText(elements.formulaHistoryState, `${jobs.length} 条`);
    jobs.forEach((job) => {
      const card = document.createElement("div");
      card.className = "formula-result-card";
      const text = document.createElement("code");
      text.textContent = job.raw_text || jobLabels[job.status] || job.status;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "ghost-button";
      button.textContent = "插入校正文";
      button.disabled = !job.raw_text;
      button.addEventListener("click", () => {
        const prefix = elements.correctedTextInput.value && !elements.correctedTextInput.value.endsWith("\n") ? "\n" : "";
        elements.correctedTextInput.value += `${prefix}${job.raw_text || ""}`;
        markDirty();
      });
      card.append(text, button);
      elements.formulaHistoryList.append(card);
    });
  }

  function drawFormulaCanvas() {
    const canvas = elements.formulaCropCanvas;
    const image = state.formulaImage;
    if (!image) return;
    const maxWidth = Math.min(900, window.innerWidth - 48);
    const scale = Math.min(1, maxWidth / image.naturalWidth);
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const selection = state.formulaSelection;
    if (selection) {
      context.fillStyle = "rgba(32, 94, 166, .18)";
      context.strokeStyle = "#205ea6";
      context.lineWidth = 3;
      context.fillRect(selection.x, selection.y, selection.width, selection.height);
      context.strokeRect(selection.x, selection.y, selection.width, selection.height);
    }
  }

  function canvasPoint(event) {
    const rect = elements.formulaCropCanvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(elements.formulaCropCanvas.width, (event.clientX - rect.left) * elements.formulaCropCanvas.width / rect.width)),
      y: Math.max(0, Math.min(elements.formulaCropCanvas.height, (event.clientY - rect.top) * elements.formulaCropCanvas.height / rect.height)),
    };
  }

  function openFormulaCrop() {
    if (!elements.questionImage.src) return;
    const image = new Image();
    image.onload = () => {
      state.formulaImage = image;
      state.formulaSelection = null;
      drawFormulaCanvas();
      elements.formulaCropDialog.showModal();
      setStateText(elements.formulaCropState, "拖动框选公式");
    };
    image.src = elements.questionImage.src;
  }

  async function submitFormulaCrop() {
    const question = state.currentQuestion;
    const selection = state.formulaSelection;
    if (!question || !selection || selection.width < 10 || selection.height < 10) {
      setStateText(elements.formulaCropState, "请先框选公式区域", "error");
      return;
    }
    const source = elements.formulaCropCanvas;
    const crop = document.createElement("canvas");
    crop.width = Math.round(selection.width);
    crop.height = Math.round(selection.height);
    crop.getContext("2d").drawImage(source, selection.x, selection.y, selection.width, selection.height, 0, 0, crop.width, crop.height);
    const blob = await new Promise((resolve) => crop.toBlob(resolve, "image/png"));
    const formData = new FormData();
    formData.append("file", blob, "formula-crop.png");
    elements.submitFormulaCropButton.disabled = true;
    try {
      const data = await requestJSON(`/api/questions/${question.question_id}/formula-ocr`, { method: "POST", body: formData });
      elements.formulaCropDialog.close();
      setStateText(elements.detailStatus, `公式 OCR 任务 #${data.job.ocr_job_id} 已创建`, "success");
      await selectQuestion(question.question_id);
    } catch (error) {
      setStateText(elements.formulaCropState, error.message, "error");
    } finally {
      elements.submitFormulaCropButton.disabled = false;
    }
  }
  function renderMathInto(element, content) {
    element.replaceChildren();
    const blockPattern = /\$\$([\s\S]*?)\$\$|\\\[([\s\S]*?)\\\]|\$([^$\n]+)\$|\\\((.*?)\\\)/g;
    let lastIndex = 0;
    for (const match of (content || "").matchAll(blockPattern)) {
      if (match.index > lastIndex) element.append(document.createTextNode(content.slice(lastIndex, match.index)));
      const formula = match[1] || match[2] || match[3] || match[4] || "";
      const node = document.createElement(match[1] || match[2] ? "div" : "span");
      if (window.katex) { try { window.katex.render(formula, node, { throwOnError: false, displayMode: Boolean(match[1] || match[2]) }); } catch { node.textContent = formula; } }
      else node.textContent = formula;
      element.append(node); lastIndex = match.index + match[0].length;
    }
    if (lastIndex < (content || "").length) element.append(document.createTextNode(content.slice(lastIndex)));
  }
  function renderLatexPreview() {
    renderMathInto(elements.latexPreviewContent, elements.correctedTextInput.value || "");
    renderMathInto(elements.answerPreview, elements.answerTextInput.value || "");
    renderMathInto(elements.solutionPreview, elements.solutionTextInput.value || "");
  }
  function renderSourceOptions(selectedSourceId = null, selectedChapterId = null) {
    const sourceOptions = ['<option value="">未选择</option>'];
    state.sources.forEach((source) => sourceOptions.push(`<option value="${source.source_id}">${escapeHtml(source.name)}</option>`));
    elements.sourceSelect.innerHTML = sourceOptions.join("");
    elements.chapterSourceInput.innerHTML = sourceOptions.join("");
    if (selectedSourceId) elements.sourceSelect.value = String(selectedSourceId);
    const sourceId = Number(elements.sourceSelect.value || selectedSourceId || 0);
    const source = state.sources.find((item) => item.source_id === sourceId);
    const chapters = source ? source.chapters || [] : [];
    elements.chapterSelect.innerHTML = '<option value="">未选择</option>' + chapters.map((chapter) => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.name)}</option>`).join("");
    const chapterOptions = chapters.map((chapter) => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.name)}</option>`).join("");
    elements.parentChapterInput.innerHTML = '<option value="">无上级章节</option>' + chapterOptions;
    elements.manualChapterSelect.innerHTML = '<option value="">未选择</option>' + chapterOptions;
    elements.bulkChapterSelect.innerHTML = '<option value="">批量章节</option>' + chapterOptions;
    if (selectedChapterId) elements.chapterSelect.value = String(selectedChapterId);
  }

  function renderSourceTree() {
    elements.sourceTree.replaceChildren();
    state.sources.forEach((source) => {
      const group = document.createElement("div"); group.className = "source-tree-group";
      const title = document.createElement("button"); title.type = "button"; title.textContent = source.name; title.dataset.sourceId = source.source_id;
      group.append(title);
      orderedChapters(source.chapters || []).forEach(({ chapter, depth }) => { const row = document.createElement("div"); row.className = "source-tree-row chapter-row"; const item = document.createElement("button"); item.type = "button"; item.style.paddingLeft = `${24 + depth * 14}px`; item.textContent = `${depth ? "└ " : "↳ "}${chapter.name}`; item.dataset.chapterId = chapter.chapter_id; const menu = document.createElement("button"); menu.type = "button"; menu.className = "tree-menu"; menu.textContent = "⋯"; menu.dataset.manageChapterId = chapter.chapter_id; row.append(item, menu); group.append(row); });
      elements.sourceTree.append(group);
    });
  }

  async function loadSources() {
    const data = await requestJSON("/api/sources");
    state.sources = data.items || [];
    renderSourceTree();
    renderSourceOptions(state.currentQuestion?.source_id, state.currentQuestion?.chapter_id);
  }

  function switchDetailTab(name) {
    elements.detailTabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.detailTab === name));
    elements.detailPanels.forEach((panel) => panel.classList.toggle("is-active", panel.dataset.detailPanel === name));
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
    elements.answerTextInput.value = question.answer_text || "";
    elements.solutionTextInput.value = question.solution_text || "";
    elements.personalSolutionInput.value = question.personal_solution || "";
    elements.keyStepsInput.value = question.key_steps || "";
    elements.wrongAnswerInput.value = question.wrong_answer || "";
    elements.mistakeAnalysisInput.value = question.mistake_analysis || "";
    elements.notesInput.value = question.notes || "";
    elements.sourcePageInput.value = question.source_page || "";
    renderSourceOptions(question.source_id, question.chapter_id);
    renderLatexPreview();
    renderKnowledgePoints((question.knowledge_points || []).map((point) => point.knowledge_point_id));
    if (elements.formulaHistoryList) renderFormulaHistory(question);
    renderAssetGallery(question);
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

    if (elements.rerunOcrButton) elements.rerunOcrButton.disabled = !firstAsset || Boolean(job && ["pending", "running"].includes(job.status));
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
    const content = elements.paddleTextInput.value.trim();
    const file = elements.galleryInput.files[0] || null;
    if (!content && !file) {
      setStateText(elements.uploadState, "请粘贴 PaddleOCR 文本或选择原题图片", "error");
      return;
    }

    elements.uploadButton.disabled = true;
    setStateText(elements.uploadState, "正在创建错题...");
    const formData = new FormData();
    formData.append("title", elements.manualTitleInput.value.trim());
    formData.append("subject", elements.manualSubjectInput.value.trim());
    formData.append("source", elements.manualSourceInput.value.trim());
    formData.append("question_type", elements.manualTypeInput.value.trim());
    formData.append("source_id", elements.manualSourceSelect.value);
    formData.append("chapter_id", elements.manualChapterSelect.value);
    formData.append("source_page", elements.manualSourcePageInput.value.trim());
    formData.append("content", content);
    if (file) formData.append("file", file);

    try {
      const data = await requestJSON("/api/questions/manual", { method: "POST", body: formData });
      elements.uploadForm.reset();
      elements.manualSourceInput.value = "PaddleOCR Web";
      elements.selectedImageName.textContent = "尚未选择图片";
      await Promise.all([loadQuestions(), loadQuestionStats()]);
      await selectQuestion(data.question.question_id);
      switchView("library");
      setStateText(elements.uploadState, `题目 #${data.question.question_id} 已创建`, "success");
    } catch (error) {
      setStateText(elements.uploadState, error.message, "error");
    } finally {
      elements.uploadButton.disabled = false;
    }
  }
  async function handleRerunOcr() {
    const question = state.currentQuestion;
    if (!question) return;
    elements.rerunOcrButton.disabled = true;
    setStateText(elements.detailStatus, "Creating a new OCR job...");
    try {
      const data = await requestJSON(`/api/questions/${question.question_id}/ocr-jobs`, { method: "POST" });
      state.currentQuestion = data.question;
      renderDetail(data.question);
      setStateText(elements.detailStatus, `OCR job #${data.job.ocr_job_id} created. Corrected text is preserved.`, "success");
      await loadQuestions();
    } catch (error) {
      setStateText(elements.detailStatus, error.message, "error");
      elements.rerunOcrButton.disabled = false;
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
      answer_text: cleanValue(elements.answerTextInput.value),
      solution_text: cleanValue(elements.solutionTextInput.value),
      personal_solution: cleanValue(elements.personalSolutionInput.value),
      key_steps: cleanValue(elements.keyStepsInput.value),
      wrong_answer: cleanValue(elements.wrongAnswerInput.value),
      mistake_analysis: cleanValue(elements.mistakeAnalysisInput.value),
      notes: cleanValue(elements.notesInput.value),
      source_id: elements.sourceSelect.value ? Number(elements.sourceSelect.value) : null,
      chapter_id: elements.chapterSelect.value ? Number(elements.chapterSelect.value) : null,
      source_page: cleanValue(elements.sourcePageInput.value),
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

  async function handleQuestionImport() {
    const file = elements.questionImportInput.files[0];
    if (!file) {
      setStateText(elements.questionImportState, "\u8bf7\u5148\u9009\u62e9 WrongBook JSON \u6587\u4ef6\u3002", true);
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    elements.importQuestionsButton.disabled = true;
    setStateText(elements.questionImportState, "\u6b63\u5728\u5bfc\u5165...");
    try {
      const response = await fetch("/api/questions/import", { method: "POST", body: formData });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "\u7b49\u5f85\u56fe\u7247");
      elements.questionImportInput.value = "";
      elements.questionImportFileLabel.textContent = "\u9009\u62e9 WrongBook JSON";
      setStateText(elements.questionImportState, `\u5df2\u5bfc\u5165 ${payload.imported_count} \u9053\u65b0\u9898\u76ee\u3002`);
      state.questionOffset = 0;
      await Promise.all([loadQuestions({ selectFirst: true }), loadQuestionStats(), loadKnowledgePoints(), loadMistakeTagSuggestions()]);
    } catch (error) {
      setStateText(elements.questionImportState, error.message, true);
    } finally {
      elements.importQuestionsButton.disabled = false;
    }
  }


  function downloadFilteredQuestions(format) {
    const params = new URLSearchParams({ format });
    const query = elements.searchInput.value.trim();
    const status = elements.statusFilter.value;
    if (query) params.set("q", query);
    if (status) params.set("status", status);
    window.location.assign(`/api/questions/export?${params.toString()}`);
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

  function switchView(viewName) {
    state.activeView = viewName;
    elements.appViews.forEach((view) => view.classList.toggle("is-mobile-active", view.dataset.view === viewName));
    elements.bottomNavItems.forEach((item) => {
      const active = item.dataset.targetView === viewName;
      item.classList.toggle("is-active", active);
      if (active) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current");
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function selectImageSources(files) {
    state.selectedImageFiles = Array.from(files || []);
    const count = state.selectedImageFiles.length;
    elements.selectedImageName.textContent = count
      ? count === 1 ? state.selectedImageFiles[0].name : `\u5df2\u9009\u62e9 ${count} \u5f20\u56fe\u7247`
      : "\u5c1a\u672a\u9009\u62e9\u56fe\u7247";
    elements.uploadButton.disabled = count === 0;
    setStateText(elements.uploadState, count ? `\u5df2\u9009\u62e9 ${count} \u5f20\uff0c\u53ef\u4ee5\u4e0a\u4f20` : "\u7b49\u5f85\u56fe\u7247", count ? "success" : "");
  }

  function setupEvents() {
    elements.uploadForm.addEventListener("submit", handleUpload);
    elements.detailForm.addEventListener("submit", handleSave);
    elements.refreshButton.addEventListener("click", () => { loadQuestions(); loadQuestionStats(); loadDueReviews(); loadReviewStats(); });
    elements.scheduleReviewButton.addEventListener("click", handleScheduleReview);
    elements.exportFilteredJsonButton.addEventListener("click", () => downloadFilteredQuestions("json"));
    elements.exportFilteredMarkdownButton.addEventListener("click", () => downloadFilteredQuestions("markdown"));
    elements.importQuestionsButton.addEventListener("click", handleQuestionImport);
    elements.questionImportInput.addEventListener("change", () => {
      const file = elements.questionImportInput.files[0];
      elements.questionImportFileLabel.textContent = file ? file.name : "\u9009\u62e9 WrongBook JSON";
      setStateText(elements.questionImportState, file ? "JSON \u6587\u4ef6\u5df2\u9009\u62e9\u3002" : "");
    });
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

    elements.cameraInput.addEventListener("change", () => {
      const file = elements.cameraInput.files[0];
      if (file) elements.galleryInput.value = "";
      selectImageSources(file ? [file] : []);
    });

    elements.galleryInput.addEventListener("change", () => {
      const file = elements.galleryInput.files[0];
      elements.selectedImageName.textContent = file ? file.name : "尚未选择图片";
    });
    elements.detailTabs.forEach((tab) => tab.addEventListener("click", () => switchDetailTab(tab.dataset.detailTab)));
    elements.correctedTextInput.addEventListener("input", renderLatexPreview);
    elements.answerTextInput.addEventListener("input", renderLatexPreview);
    elements.solutionTextInput.addEventListener("input", renderLatexPreview);
    elements.sourceSelect.addEventListener("change", () => { renderSourceOptions(Number(elements.sourceSelect.value || 0), null); markDirty(); });
    elements.chapterSelect.addEventListener("change", markDirty);
    elements.openSourceDialogButton.addEventListener("click", () => { renderSourceOptions(); elements.sourceDialog.showModal(); });
    elements.closeSourceDialogButton.addEventListener("click", () => elements.sourceDialog.close());
    elements.chapterSourceInput.addEventListener("change", () => {
      const source = state.sources.find((item) => item.source_id === Number(elements.chapterSourceInput.value));
      elements.parentChapterInput.innerHTML = '<option value="">无上级章节</option>' + ((source?.chapters || []).map((chapter) => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.name)}</option>`).join(""));
    });
    elements.sourceForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await requestJSON("/api/sources", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: elements.sourceNameInput.value, subject: elements.sourceSubjectInput.value || null, source_type: elements.sourceTypeInput.value || null }) });
        elements.sourceForm.reset(); await loadSources(); setStateText(elements.sourceDialogState, "资料已创建", "success");
      } catch (error) { setStateText(elements.sourceDialogState, error.message, "error"); }
    });
    elements.chapterForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await requestJSON("/api/chapters", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: Number(elements.chapterSourceInput.value), parent_id: elements.parentChapterInput.value ? Number(elements.parentChapterInput.value) : null, name: elements.chapterNameInput.value }) });
        elements.chapterForm.reset(); await loadSources(); setStateText(elements.sourceDialogState, "章节已创建", "success");
      } catch (error) { setStateText(elements.sourceDialogState, error.message, "error"); }
    });
    elements.sourceTree.addEventListener("click", (event) => {
      const target = event.target.closest("button"); if (!target) return;
      state.sourceFilterId = target.dataset.sourceId ? Number(target.dataset.sourceId) : null;
      state.chapterFilterId = target.dataset.chapterId ? Number(target.dataset.chapterId) : null;
      if (state.chapterFilterId) {
        const owner = state.sources.find((item) => (item.chapters || []).some((chapter) => chapter.chapter_id === state.chapterFilterId));
        state.sourceFilterId = owner?.source_id || null;
      }
      elements.searchInput.value = "";
      state.questionOffset = 0; loadQuestions();
    });
    elements.uploadAssetsButton.addEventListener("click", async () => {
      const question = state.currentQuestion; const files = Array.from(elements.newAssetInput.files || []);
      if (!question || !files.length) { setStateText(elements.assetState, "请选择图片", "error"); return; }
      elements.uploadAssetsButton.disabled = true;
      try {
        for (const file of files) { const formData = new FormData(); formData.append("asset_type", elements.newAssetType.value); formData.append("file", file); await requestJSON(`/api/questions/${question.question_id}/assets`, { method: "POST", body: formData }); }
        elements.newAssetInput.value = ""; await selectQuestion(question.question_id); setStateText(elements.assetState, `已上传 ${files.length} 张附件`, "success");
      } catch (error) { setStateText(elements.assetState, error.message, "error"); } finally { elements.uploadAssetsButton.disabled = false; }
    });
    elements.closeAssetPreviewButton.addEventListener("click", () => elements.assetPreviewDialog.close());
    elements.smartFolders.addEventListener("click", (event) => {
      const target = event.target.closest("button"); if (!target) return;
      state.smartFilter = target.dataset.smartFilter || "";
      state.sourceFilterId = null; state.chapterFilterId = null; state.questionOffset = 0;
      elements.smartFolders.querySelectorAll("button").forEach((button) => button.classList.toggle("is-active", button === target));
      loadQuestions();
    });
    elements.cardViewButton.addEventListener("click", () => { state.questionView = "card"; elements.cardViewButton.classList.add("is-active"); elements.tableViewButton.classList.remove("is-active"); renderQuestionList(state.questionTotal); });
    elements.tableViewButton.addEventListener("click", () => { state.questionView = "table"; elements.tableViewButton.classList.add("is-active"); elements.cardViewButton.classList.remove("is-active"); renderQuestionList(state.questionTotal); });
    elements.manualSourceSelect.addEventListener("change", () => {
      const source = state.sources.find((item) => item.source_id === Number(elements.manualSourceSelect.value));
      elements.manualChapterSelect.innerHTML = '<option value="">未选择</option>' + ((source?.chapters || []).map((chapter) => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.name)}</option>`).join(""));
    });
    elements.bulkSourceSelect.addEventListener("change", () => {
      const source = state.sources.find((item) => item.source_id === Number(elements.bulkSourceSelect.value));
      elements.bulkChapterSelect.innerHTML = '<option value="">批量章节</option>' + ((source?.chapters || []).map((chapter) => `<option value="${chapter.chapter_id}">${escapeHtml(chapter.name)}</option>`).join(""));
    });
    elements.selectPageQuestions.addEventListener("change", () => {
      state.questions.forEach((question) => { if (elements.selectPageQuestions.checked) state.selectedQuestionIds.add(question.question_id); else state.selectedQuestionIds.delete(question.question_id); });
      renderQuestionList(state.questionTotal);
    });
    elements.applyBulkButton.addEventListener("click", async () => {
      const questionIds = Array.from(state.selectedQuestionIds);
      if (!questionIds.length) { setStateText(elements.bulkState, "请先选择题目", "error"); return; }
      try {
        const result = await requestJSON("/api/questions/bulk-update", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question_ids: questionIds, source_id: elements.bulkSourceSelect.value ? Number(elements.bulkSourceSelect.value) : null, chapter_id: elements.bulkChapterSelect.value ? Number(elements.bulkChapterSelect.value) : null, status: elements.bulkStatusSelect.value || null }) });
        state.selectedQuestionIds.clear(); elements.selectPageQuestions.checked = false; await loadQuestions(); setStateText(elements.bulkState, `已更新 ${result.updated_count} 道题`, "success");
      } catch (error) { setStateText(elements.bulkState, error.message, "error"); }
    });
    elements.bottomNavItems.forEach((item) => {
      item.addEventListener("click", () => switchView(item.dataset.targetView));
    });

    if (elements.rerunOcrButton) elements.rerunOcrButton.addEventListener("click", handleRerunOcr);
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
      elements.answerTextInput,
      elements.solutionTextInput,
      elements.personalSolutionInput,
      elements.keyStepsInput,
      elements.wrongAnswerInput,
      elements.mistakeAnalysisInput,
      elements.notesInput,
      elements.sourcePageInput,
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
  switchView(state.activeView);
  registerServiceWorker();
  loadQuestions({ selectFirst: true });
  loadQuestionStats();
  loadKnowledgePoints();
  loadSources();
  loadMistakeTagSuggestions();
})();
