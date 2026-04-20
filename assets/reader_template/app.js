const state = {
  config: null,
  evidenceMap: null,
  pageManifest: null,
  currentDocKey: null,
  activeClaimId: null,
  activeEvidenceId: null,
  pdfZoom: 1,
  renderedPages: new Map(),
  claimNodes: new Map(),
};

const elements = {
  appTitle: document.getElementById("app-title"),
  assetLinks: document.getElementById("asset-links"),
  docSwitch: document.getElementById("doc-switch"),
  pdfStatus: document.getElementById("pdf-status"),
  zoomOut: document.getElementById("zoom-out"),
  zoomFit: document.getElementById("zoom-fit"),
  zoomIn: document.getElementById("zoom-in"),
  zoomLabel: document.getElementById("zoom-label"),
  pdfScroll: document.getElementById("pdf-scroll"),
  evidenceList: document.getElementById("evidence-list"),
  activeClaimLabel: document.getElementById("active-claim-label"),
  claimIndex: document.getElementById("claim-index"),
  reportRoot: document.getElementById("report-root"),
};

const CLAIM_MARKER = /^\[(C\d+\.\d+)\]\s*/;
const MIN_PDF_ZOOM = 0.65;
const MAX_PDF_ZOOM = 3;
const PDF_ZOOM_STEP = 0.15;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
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
  div.className = `highlight-rect${focused ? " focused" : ""}`;
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

function renderEvidenceList(claimId) {
  const claim = getClaim(claimId);
  if (!claim || !claim.evidence.length) {
    elements.evidenceList.innerHTML = `<p class="muted">No evidence available for this claim.</p>`;
    return;
  }

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
            <strong>${escapeHtml(item.quote)}</strong>
            <p>${escapeHtml(item.paragraph_text || "No paragraph excerpt available.")}</p>
            <span class="evidence-path">${escapeHtml(anchorLabel)}</span>
          </div>
          <button type="button" data-index="${index}">Locate</button>
        </div>
      `;
    })
    .join("");

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
  elements.activeClaimLabel.textContent = `${claim.claim_id} ${claim.claim_text}`;

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
        const button = document.createElement("button");
        button.type = "button";
        button.className = "claim-card";
        button.innerHTML = `
          <div class="claim-card__meta">
            <span class="claim-tag">${escapeHtml(claim.claim_id)}</span>
            <span class="claim-count">${claim.evidence.length} evidence item(s)</span>
          </div>
          <div class="claim-text">${escapeHtml(claim.claim_text)}</div>
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
  renderAssetLinks();
  wireZoomControls();
  buildDocSwitch();
  renderDocumentImages(state.currentDocKey);
  buildClaimIndex();

  elements.reportRoot.innerHTML = reportHtml;
  wireReportClaims();

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
          renderDocumentImages(state.currentDocKey);
          if (state.activeClaimId) {
            applyHighlights(state.activeClaimId, state.activeEvidenceId);
          }
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
