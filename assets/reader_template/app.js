const state = {
  config: null,
  evidenceMap: null,
  pageManifest: null,
  researchLens: null,
  currentDocKey: null,
  activeClaimId: null,
  activeEvidenceId: null,
  pdfZoom: 1,
  renderedPages: new Map(),
  claimNodes: new Map(),
};

const elements = {
  appTitle: document.getElementById("app-title"),
  appSubtitle: document.getElementById("app-subtitle"),
  assetLinks: document.getElementById("asset-links"),
  panePdf: document.querySelector(".pane-pdf"),
  docSwitch: document.getElementById("doc-switch"),
  pdfStatus: document.getElementById("pdf-status"),
  zoomOut: document.getElementById("zoom-out"),
  zoomFit: document.getElementById("zoom-fit"),
  zoomIn: document.getElementById("zoom-in"),
  zoomLabel: document.getElementById("zoom-label"),
  evidencePanel: document.getElementById("evidence-panel"),
  pdfEvidenceResizer: document.getElementById("pdf-evidence-resizer"),
  pdfScroll: document.getElementById("pdf-scroll"),
  evidenceList: document.getElementById("evidence-list"),
  activeClaimLabel: document.getElementById("active-claim-label"),
  researchStrip: document.getElementById("research-strip"),
  claimIndex: document.getElementById("claim-index"),
  reportRoot: document.getElementById("report-root"),
};

const CLAIM_MARKER = /^\[(C\d+\.\d+)\]\s*/;
const MIN_PDF_ZOOM = 0.65;
const MAX_PDF_ZOOM = 3;
const PDF_ZOOM_STEP = 0.15;
const EVIDENCE_PANEL_STORAGE_KEY = "paper-reader:evidence-panel-height";
const MIN_EVIDENCE_PANEL_HEIGHT = 112;
const MIN_PDF_VIEWPORT_HEIGHT = 220;
const EVIDENCE_RESIZE_KEYBOARD_STEP = 28;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderTrustedHtml(preferredValue, fallbackValue = "") {
  return preferredValue || escapeHtml(fallbackValue);
}

function uniqueClaimIds(claimIds = []) {
  return [...new Set((claimIds || []).filter(Boolean))];
}

function safeStorage(action, fallback = null) {
  try {
    return action();
  } catch (error) {
    return fallback;
  }
}

function getEvidencePanelHeightBounds() {
  const paneHeight = elements.panePdf?.clientHeight || 0;
  const toolbarHeight = elements.panePdf?.querySelector(".pane-toolbar")?.offsetHeight || 0;
  const resizerHeight = elements.pdfEvidenceResizer?.offsetHeight || 14;
  const available = Math.max(0, paneHeight - toolbarHeight - resizerHeight);
  const minPdfHeight = Math.min(
    MIN_PDF_VIEWPORT_HEIGHT,
    Math.max(132, Math.round(available * 0.46))
  );
  const min = MIN_EVIDENCE_PANEL_HEIGHT;
  const max = Math.max(min, available - minPdfHeight);
  return { min, max, available };
}

function getDefaultEvidencePanelHeight() {
  const { min, max, available } = getEvidencePanelHeightBounds();
  if (!available) {
    return 176;
  }
  return Math.min(max, Math.max(min, Math.round(available * 0.24)));
}

function updateEvidenceResizerAria(height) {
  if (!elements.pdfEvidenceResizer) {
    return;
  }
  const { min, max } = getEvidencePanelHeightBounds();
  elements.pdfEvidenceResizer.setAttribute("aria-valuemin", String(min));
  elements.pdfEvidenceResizer.setAttribute("aria-valuemax", String(max));
  elements.pdfEvidenceResizer.setAttribute("aria-valuenow", String(Math.round(height)));
}

function setEvidencePanelHeight(height, options = {}) {
  if (!elements.evidencePanel) {
    return 0;
  }

  const { persist = true } = options;
  const { min, max } = getEvidencePanelHeightBounds();
  const nextHeight = Math.min(max, Math.max(min, Math.round(height)));
  elements.evidencePanel.style.height = `${nextHeight}px`;
  elements.evidencePanel.style.flexBasis = `${nextHeight}px`;
  updateEvidenceResizerAria(nextHeight);

  if (persist) {
    safeStorage(() => window.localStorage.setItem(EVIDENCE_PANEL_STORAGE_KEY, String(nextHeight)));
  }
  return nextHeight;
}

function refreshPdfViewport(preserveScroll = true) {
  if (!state.currentDocKey) {
    return;
  }
  renderDocumentImages(state.currentDocKey, { preserveScroll });
  if (state.activeClaimId) {
    applyHighlights(state.activeClaimId, state.activeEvidenceId);
  }
}

function wireEvidenceResizer() {
  const resizer = elements.pdfEvidenceResizer;
  const evidencePanel = elements.evidencePanel;
  if (!resizer || !evidencePanel) {
    return;
  }

  const storedHeight = safeStorage(
    () => Number(window.localStorage.getItem(EVIDENCE_PANEL_STORAGE_KEY)),
    NaN
  );
  const initialHeight =
    Number.isFinite(storedHeight) && storedHeight > 0
      ? storedHeight
      : getDefaultEvidencePanelHeight();
  setEvidencePanelHeight(initialHeight, { persist: Number.isFinite(storedHeight) && storedHeight > 0 });

  let dragState = null;

  const finishResize = (pointerId = null) => {
    if (!dragState) {
      return;
    }
    document.body.classList.remove("is-resizing");
    if (pointerId !== null) {
      try {
        resizer.releasePointerCapture(pointerId);
      } catch (error) {
        // Ignore release failures when the pointer capture lifecycle already ended.
      }
    }
    setEvidencePanelHeight(dragState.lastHeight, { persist: true });
    dragState = null;
    refreshPdfViewport(true);
  };

  resizer.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    dragState = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startHeight: evidencePanel.getBoundingClientRect().height,
      lastHeight: evidencePanel.getBoundingClientRect().height,
    };
    document.body.classList.add("is-resizing");
    resizer.focus({ preventScroll: true });
    resizer.setPointerCapture?.(event.pointerId);
  });

  resizer.addEventListener("pointermove", (event) => {
    if (!dragState || event.pointerId !== dragState.pointerId) {
      return;
    }
    const nextHeight = dragState.startHeight + (event.clientY - dragState.startY);
    dragState.lastHeight = setEvidencePanelHeight(nextHeight, { persist: false });
  });

  resizer.addEventListener("pointerup", (event) => {
    if (!dragState || event.pointerId !== dragState.pointerId) {
      return;
    }
    finishResize(event.pointerId);
  });

  resizer.addEventListener("pointercancel", (event) => {
    if (!dragState || event.pointerId !== dragState.pointerId) {
      return;
    }
    finishResize(event.pointerId);
  });

  resizer.addEventListener("dblclick", () => {
    setEvidencePanelHeight(getDefaultEvidencePanelHeight(), { persist: true });
    refreshPdfViewport(true);
  });

  resizer.addEventListener("keydown", (event) => {
    const currentHeight = evidencePanel.getBoundingClientRect().height;
    let nextHeight = null;

    switch (event.key) {
      case "ArrowUp":
        nextHeight = currentHeight - EVIDENCE_RESIZE_KEYBOARD_STEP;
        break;
      case "ArrowDown":
        nextHeight = currentHeight + EVIDENCE_RESIZE_KEYBOARD_STEP;
        break;
      case "Home":
        nextHeight = getEvidencePanelHeightBounds().min;
        break;
      case "End":
        nextHeight = getEvidencePanelHeightBounds().max;
        break;
      case "Enter":
      case " ":
        nextHeight = getDefaultEvidencePanelHeight();
        break;
      default:
        return;
    }

    event.preventDefault();
    setEvidencePanelHeight(nextHeight, { persist: true });
    refreshPdfViewport(true);
  });
}

function getClaim(claimId) {
  return state.evidenceMap?.claims?.[claimId] || null;
}

function registerClaimNode(claimId, node) {
  if (!state.claimNodes.has(claimId)) {
    state.claimNodes.set(claimId, new Set());
  }
  state.claimNodes.get(claimId).add(node);
}

function setActiveClaimUI(claimId) {
  state.claimNodes.forEach((nodes, key) => {
    nodes.forEach((node) => node.classList.toggle("active", key === claimId));
  });
}

function renderAssetLinks() {
  elements.assetLinks.innerHTML = "";
  for (const link of state.config.links || []) {
    const anchor = document.createElement("a");
    anchor.href = link.href;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = link.label;
    elements.assetLinks.appendChild(anchor);
  }
}

function buildDocSwitch() {
  elements.docSwitch.innerHTML = "";
  for (const [docKey, doc] of Object.entries(state.config.documents || {})) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = doc.label;
    button.classList.toggle("active", docKey === state.currentDocKey);
    button.addEventListener("click", () => setDocument(docKey));
    elements.docSwitch.appendChild(button);
  }
}

function clampPdfZoom(value) {
  return Math.min(MAX_PDF_ZOOM, Math.max(MIN_PDF_ZOOM, value));
}

function updateZoomLabel() {
  if (!elements.zoomLabel) {
    return;
  }
  elements.zoomLabel.textContent = `${Math.round(state.pdfZoom * 100)}%`;
}

function getScrollAnchor() {
  const scroll = elements.pdfScroll;
  if (!scroll || !scroll.scrollWidth || !scroll.scrollHeight) {
    return null;
  }
  return {
    x: (scroll.scrollLeft + scroll.clientWidth / 2) / scroll.scrollWidth,
    y: (scroll.scrollTop + scroll.clientHeight / 2) / scroll.scrollHeight,
  };
}

function restoreScrollAnchor(anchor) {
  if (!anchor) {
    return;
  }
  const scroll = elements.pdfScroll;
  scroll.scrollLeft = Math.max(0, anchor.x * scroll.scrollWidth - scroll.clientWidth / 2);
  scroll.scrollTop = Math.max(0, anchor.y * scroll.scrollHeight - scroll.clientHeight / 2);
}

function renderDocumentImages(docKey, options = {}) {
  const manifest = state.pageManifest[docKey];
  if (!manifest) {
    throw new Error(`No page manifest for ${docKey}`);
  }

  const docLabel = state.config.documents[docKey]?.label || docKey;
  elements.pdfStatus.textContent = `Loading ${docLabel} pages...`;
  const scrollAnchor = options.preserveScroll ? getScrollAnchor() : null;
  elements.pdfScroll.innerHTML = "";
  state.renderedPages.clear();

  const scrollWidth = elements.pdfScroll.clientWidth || 800;
  const scrollHeight = elements.pdfScroll.clientHeight || 900;
  manifest.pages.forEach((page) => {
    const fitWidth = Math.max(220, scrollWidth - 24);
    const fitHeight = Math.max(280, scrollHeight - 10);
    const widthScale = fitWidth / page.width;
    const heightScale = fitHeight / page.height;
    const fitScale = Math.min(widthScale, heightScale, 1);
    const scale = fitScale * state.pdfZoom;
    const targetWidth = Math.round(page.width * scale);

    const pageWrapper = document.createElement("section");
    pageWrapper.className = "pdf-page";
    pageWrapper.dataset.page = String(page.number);
    pageWrapper.dataset.doc = docKey;
    pageWrapper.style.width = `${targetWidth}px`;

    const pageLabel = document.createElement("div");
    pageLabel.className = "pdf-page__label";
    pageLabel.textContent = `${docLabel} page ${page.number}`;
    pageWrapper.appendChild(pageLabel);

    const image = document.createElement("img");
    image.className = "pdf-canvas";
    image.src = page.image;
    image.alt = `${docLabel} page ${page.number}`;
    image.width = targetWidth;
    image.height = Math.round(page.height * scale);
    image.loading = "lazy";
    pageWrapper.appendChild(image);

    const overlay = document.createElement("div");
    overlay.className = "highlight-layer";
    pageWrapper.appendChild(overlay);

    elements.pdfScroll.appendChild(pageWrapper);
    state.renderedPages.set(page.number, {
      pageWrapper,
      overlay,
      scaleX: scale,
      scaleY: scale,
    });
  });

  elements.pdfStatus.textContent = `${docLabel} loaded with ${manifest.pages.length} page(s).`;
  updateZoomLabel();
  restoreScrollAnchor(scrollAnchor);
}

function setPdfZoom(nextZoom) {
  state.pdfZoom = clampPdfZoom(nextZoom);
  if (!state.currentDocKey) {
    updateZoomLabel();
    return;
  }
  renderDocumentImages(state.currentDocKey, { preserveScroll: true });
  if (state.activeClaimId) {
    applyHighlights(state.activeClaimId, state.activeEvidenceId);
  }
}

function wireZoomControls() {
  elements.zoomOut?.addEventListener("click", () => setPdfZoom(state.pdfZoom - PDF_ZOOM_STEP));
  elements.zoomIn?.addEventListener("click", () => setPdfZoom(state.pdfZoom + PDF_ZOOM_STEP));
  elements.zoomFit?.addEventListener("click", () => setPdfZoom(1));
  updateZoomLabel();
}

function clearHighlights() {
  for (const pageData of state.renderedPages.values()) {
    pageData.overlay.innerHTML = "";
  }
}

function addHighlightRect(match, focused = false) {
  const pageData = state.renderedPages.get(match.page);
  if (!pageData) {
    return null;
  }

  const [x0, y0, x1, y1] = match.rect;
  const div = document.createElement("div");
  const granularityClass =
    match.granularity === "paragraph-block"
      ? " highlight-rect--paragraph"
      : match.granularity === "line-cluster"
      ? " highlight-rect--cluster"
      : "";
  div.className = `highlight-rect${granularityClass}${focused ? " focused" : ""}`;
  if (match.granularity) {
    div.dataset.granularity = match.granularity;
  }
  div.style.left = `${x0 * pageData.scaleX}px`;
  div.style.top = `${y0 * pageData.scaleY}px`;
  div.style.width = `${(x1 - x0) * pageData.scaleX}px`;
  div.style.height = `${(y1 - y0) * pageData.scaleY}px`;
  pageData.overlay.appendChild(div);
  return { pageWrapper: pageData.pageWrapper };
}

function getEvidenceForDoc(claimId, docKey) {
  const claim = getClaim(claimId);
  if (!claim) {
    return [];
  }
  return claim.evidence.filter((item) => item.doc === docKey);
}

function renderClaimChipRow(claimIds) {
  const ids = uniqueClaimIds(claimIds);
  if (!ids.length) {
    return "";
  }
  return `
    <div class="claim-chip-row">
      ${ids
        .map(
          (claimId) =>
            `<button type="button" class="claim-chip" data-claim-id="${escapeHtml(claimId)}">${escapeHtml(
              claimId
            )}</button>`
        )
        .join("")}
    </div>
  `;
}

function bindClaimChipHandlers(root) {
  root.querySelectorAll("button[data-claim-id]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      activateClaim(button.dataset.claimId);
    });
  });
}

function renderResearchLensCard(title, bodyHtml, claimIds = []) {
  return `
    <article class="research-card">
      <div class="research-card__title">${escapeHtml(title)}</div>
      <div class="research-card__body">${bodyHtml}</div>
      ${renderClaimChipRow(claimIds)}
    </article>
  `;
}

function formatResearchField(label, value) {
  if (!value) {
    return "";
  }
  return `
    <div class="research-field">
      <span class="research-field__label">${escapeHtml(label)}</span>
      <span class="research-field__value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderBulletList(items, formatter) {
  if (!items?.length) {
    return "";
  }
  return `<ul class="research-list">${items.map(formatter).join("")}</ul>`;
}

function renderResearchLens() {
  const lens = state.researchLens;
  if (!lens || !elements.researchStrip) {
    return;
  }

  const cards = [];
  const equation = lens.research_equation || {};
  if (equation.one_sentence_thesis) {
    cards.push(
      renderResearchLensCard(
        "Research Equation",
        `
          <p class="research-lead">${escapeHtml(equation.one_sentence_thesis)}</p>
          <div class="research-field-grid">
            ${formatResearchField("Old Success", equation.valuable_paradigm)}
            ${formatResearchField("Broken Assumption", equation.broken_assumption)}
            ${formatResearchField("Hard Setting", equation.hard_setting)}
            ${formatResearchField("Borrowed Tool", equation.borrowed_tool)}
            ${formatResearchField("Missing Y", equation.unavailable_mechanism)}
            ${formatResearchField("Surrogate Z", equation.surrogate_mechanism)}
          </div>
        `,
        equation.claim_ids
      )
    );
  }

  const direction = lens.direction_reconstruction || {};
  if (
    direction.starting_dissatisfaction ||
    direction.almost_worked_transfer ||
    direction.blocking_constraint ||
    direction.replacement_logic
  ) {
    cards.push(
      renderResearchLensCard(
        "Direction Reconstruction",
        renderBulletList(
          [
            ["Starting dissatisfaction", direction.starting_dissatisfaction],
            ["Almost-worked transfer", direction.almost_worked_transfer],
            ["Blocking constraint", direction.blocking_constraint],
            ["Replacement logic", direction.replacement_logic],
          ].filter(([, value]) => value),
          ([label, value]) =>
            `<li><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</li>`
        ),
        direction.claim_ids
      )
    );
  }

  if (lens.challenge_module_map?.length) {
    cards.push(
      renderResearchLensCard(
        "Challenge → Module Map",
        renderBulletList(
          lens.challenge_module_map.slice(0, 4),
          (item) =>
            `<li><strong>${escapeHtml(item.challenge || "Challenge")}:</strong> ${escapeHtml(
              item.module || "module"
            )} via ${escapeHtml(item.design_principle || "design principle")}<span class="research-inline-note">Failure: ${escapeHtml(
              item.failure_mode || "n/a"
            )}. Evidence: ${escapeHtml(item.ablation_or_evidence || "n/a")}.</span></li>`
        ),
        lens.challenge_module_map.flatMap((item) => item.claim_ids || [])
      )
    );
  }

  if (lens.story_patterns?.length) {
    cards.push(
      renderResearchLensCard(
        "Story Pattern Worth Reusing",
        renderBulletList(
          lens.story_patterns.slice(0, 3),
          (item) =>
            `<li><strong>${escapeHtml(item.pattern_name || "Pattern")}:</strong> ${escapeHtml(
              item.formula || item.lesson || ""
            )}<span class="research-inline-note">${escapeHtml(item.lesson || "")}</span></li>`
        ),
        lens.story_patterns.flatMap((item) => item.claim_ids || [])
      )
    );
  }

  if (lens.boundary_directions?.length) {
    cards.push(
      renderResearchLensCard(
        "Boundary-Pushing Directions",
        renderBulletList(
          lens.boundary_directions.slice(0, 3),
          (item) =>
            `<li><strong>${escapeHtml(item.title || "Next idea")}:</strong> ${escapeHtml(
              item.new_direction || ""
            )}<span class="research-inline-note">Assumption: ${escapeHtml(
              item.hidden_assumption || "n/a"
            )}. Break: ${escapeHtml(item.what_breaks || "n/a")}.</span></li>`
        ),
        lens.boundary_directions.flatMap((item) => item.claim_ids || [])
      )
    );
  }

  if (!cards.length) {
    elements.researchStrip.hidden = true;
    elements.researchStrip.innerHTML = "";
    return;
  }

  elements.researchStrip.hidden = false;
  elements.researchStrip.innerHTML = `
    <section class="research-strip__header">
      <div>
        <strong>Research Lens</strong>
        <span class="muted">Grounded summary cards linked back to report claims.</span>
      </div>
    </section>
    <div class="research-grid">${cards.join("")}</div>
  `;
  bindClaimChipHandlers(elements.researchStrip);
}

function renderEvidenceList(claimId) {
  const claim = getClaim(claimId);
  if (!claim || !claim.evidence.length) {
    elements.evidenceList.innerHTML = `<p class="muted">No evidence available for this claim.</p>`;
    return;
  }

  const claimMeta = [claim.interpretation_type, claim.research_role].filter(Boolean).join(" · ");
  elements.evidenceList.innerHTML = claim.evidence
    .map((item, index) => {
      const docLabel = state.config.documents[item.doc]?.label || item.doc;
      const sectionPath = item.section_path?.length ? item.section_path.join(" / ") : "Unspecified";
      const lineLabel =
        item.line_start && item.line_end
          ? `L${item.line_start}-${item.line_end}`
          : "";
      const anchorLabel = [item.paragraph_id || sectionPath, lineLabel, item.match_source]
        .filter(Boolean)
        .join(" | ");
      return `
        <div class="evidence-item">
          <div class="evidence-meta">
            <span>${escapeHtml(docLabel)}</span>
            <span>${escapeHtml(item.relation || "direct")}</span>
          </div>
          <div class="evidence-copy">
            <strong>${renderTrustedHtml(item.quote_html, item.quote)}</strong>
            <p>${renderTrustedHtml(item.paragraph_html, item.paragraph_text || "No paragraph excerpt available.")}</p>
            <span class="evidence-path">${escapeHtml(anchorLabel)}</span>
          </div>
          <button type="button" data-index="${index}">Locate</button>
        </div>
      `;
    })
    .join("");

  if (claimMeta) {
    elements.evidenceList.insertAdjacentHTML(
      "afterbegin",
      `<div class="evidence-claim-meta">${escapeHtml(claimMeta)}</div>`
    );
  }

  elements.evidenceList.querySelectorAll("button[data-index]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      const index = Number(button.dataset.index);
      const item = claim.evidence[index];
      state.activeEvidenceId = item.evidence_id;
      if (item.doc !== state.currentDocKey) {
        await setDocument(item.doc);
      }
      applyHighlights(claimId, item.evidence_id);
    });
  });
}

function applyHighlights(claimId, focusedEvidenceId = null) {
  clearHighlights();
  const evidenceItems = getEvidenceForDoc(claimId, state.currentDocKey);
  if (!evidenceItems.length) {
    return;
  }

  let firstAnchor = null;
  evidenceItems.forEach((item) => {
    const focused = focusedEvidenceId ? item.evidence_id === focusedEvidenceId : false;
    item.matches.forEach((match) => {
      const anchor = addHighlightRect(match, focused);
      if (!firstAnchor || focused) {
        firstAnchor = anchor;
      }
    });
  });

  if (firstAnchor) {
    firstAnchor.pageWrapper.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function scrollClaimIntoView(claimId) {
  const nodes = state.claimNodes.get(claimId);
  if (!nodes || !nodes.size) {
    return;
  }
  const node = [...nodes][0];
  node.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function activateClaim(claimId, options = {}) {
  const claim = getClaim(claimId);
  if (!claim) {
    return;
  }

  state.activeClaimId = claimId;
  state.activeEvidenceId = null;
  setActiveClaimUI(claimId);
  elements.activeClaimLabel.innerHTML = `
    <span class="claim-active-id">${escapeHtml(claim.claim_id)}</span>
    <span class="claim-active-text">${renderTrustedHtml(claim.claim_text_html, claim.claim_text)}</span>
  `;

  const docKeys = [...new Set(claim.evidence.map((item) => item.doc))];
  if (docKeys.length && !docKeys.includes(state.currentDocKey)) {
    await setDocument(docKeys[0]);
  }

  renderEvidenceList(claimId);
  renderDocumentImages(state.currentDocKey, { preserveScroll: true });
  applyHighlights(claimId);
  if (options.scrollReport !== false) {
    scrollClaimIntoView(claimId);
  }
}

function buildClaimIndex() {
  const claims = Object.values(state.evidenceMap.claims || {});
  const grouped = new Map();

  claims.forEach((claim) => {
    if (!grouped.has(claim.section_id)) {
      grouped.set(claim.section_id, { title: claim.section_title, claims: [] });
    }
    grouped.get(claim.section_id).claims.push(claim);
  });

  elements.claimIndex.innerHTML = "";
  [...grouped.entries()]
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .forEach(([sectionId, group]) => {
      const groupEl = document.createElement("section");
      groupEl.className = "claim-group";

      const heading = document.createElement("h2");
      heading.textContent = `${sectionId}. ${group.title}`;
      groupEl.appendChild(heading);

      group.claims.forEach((claim) => {
        const claimMeta = [claim.interpretation_type, claim.research_role].filter(Boolean).join(" · ");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "claim-card";
        button.innerHTML = `
          <div class="claim-card__meta">
            <span class="claim-tag">${escapeHtml(claim.claim_id)}</span>
            <span class="claim-count">${claim.evidence.length} evidence item(s)</span>
          </div>
          <div class="claim-text">${renderTrustedHtml(claim.claim_text_html, claim.claim_text)}</div>
          ${claimMeta ? `<div class="claim-secondary">${escapeHtml(claimMeta)}</div>` : ""}
        `;
        button.addEventListener("click", () => activateClaim(claim.claim_id));
        registerClaimNode(claim.claim_id, button);
        groupEl.appendChild(button);
      });

      elements.claimIndex.appendChild(groupEl);
    });
}

function wireReportClaims() {
  elements.reportRoot.querySelectorAll("li, p").forEach((node) => {
    const text = node.textContent.trim();
    const match = text.match(CLAIM_MARKER);
    if (!match) {
      return;
    }

    const claimId = match[1];
    node.classList.add("report-claim");
    node.dataset.claimId = claimId;
    const labelNode =
      node.tagName === "LI" && node.firstElementChild?.tagName === "P"
        ? node.firstElementChild
        : node;
    labelNode.innerHTML = labelNode.innerHTML.replace(
      /^\s*\[(C\d+\.\d+)\]\s*/,
      '<span class="claim-tag">$1</span> '
    );
    node.addEventListener("click", () => activateClaim(claimId, { scrollReport: false }));
    registerClaimNode(claimId, node);
  });
}

async function setDocument(docKey) {
  if (!state.pageManifest[docKey]) {
    return;
  }
  state.currentDocKey = docKey;
  buildDocSwitch();
  state.pdfZoom = 1;
  renderDocumentImages(docKey);
  if (state.activeClaimId) {
    applyHighlights(state.activeClaimId, state.activeEvidenceId);
  }
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

async function loadText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.text();
}

async function boot() {
  const [config, evidenceMap, pageManifest, reportHtml] = await Promise.all([
    loadJson("./bundle-config.json"),
    loadJson("./evidence-map.json"),
    loadJson("./page-manifest.json"),
    loadText("./report.html"),
  ]);

  state.config = config;
  state.evidenceMap = evidenceMap;
  state.pageManifest = pageManifest;
  state.currentDocKey = config.default_doc;

  document.title = config.title || "Paper Evidence Reader";
  elements.appTitle.textContent = config.title || "Paper Evidence Reader";
  elements.appSubtitle.textContent =
    config.subtitle || "Trace grounded claims, inspect evidence, and mine reusable idea patterns.";
  renderAssetLinks();
  wireZoomControls();
  wireEvidenceResizer();
  buildDocSwitch();
  renderDocumentImages(state.currentDocKey);
  buildClaimIndex();

  elements.reportRoot.innerHTML = reportHtml;
  wireReportClaims();

  if (config.research_lens) {
    try {
      state.researchLens = await loadJson(config.research_lens);
      renderResearchLens();
    } catch (error) {
      console.warn("Failed to load research lens:", error);
    }
  }

  const firstClaimId = Object.keys(state.evidenceMap.claims || {})[0];
  if (firstClaimId) {
    activateClaim(firstClaimId);
  }
}

window.addEventListener(
  "resize",
  (() => {
    let timer = null;
    return () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (state.currentDocKey) {
          if (elements.evidencePanel) {
            const currentHeight = elements.evidencePanel.getBoundingClientRect().height;
            setEvidencePanelHeight(currentHeight, { persist: false });
          }
          refreshPdfViewport(true);
        }
      }, 180);
    };
  })()
);

boot().catch((error) => {
  elements.pdfStatus.textContent = "Failed to load reader assets.";
  elements.evidenceList.innerHTML = `<pre>${escapeHtml(String(error))}</pre>`;
  console.error(error);
});
