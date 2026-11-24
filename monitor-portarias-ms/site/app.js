const state = {
  records: [],
  contagemOnly: false,
};

const elements = {
  records: document.querySelector("#records"),
  empty: document.querySelector("#empty-state"),
  resultCount: document.querySelector("#result-count"),
  recordCount: document.querySelector("#record-count"),
  updated: document.querySelector("#updated-at"),
  search: document.querySelector("#search"),
  source: document.querySelector("#source-filter"),
  type: document.querySelector("#type-filter"),
  relevance: document.querySelector("#relevance-filter"),
  from: document.querySelector("#date-from"),
  to: document.querySelector("#date-to"),
  allButton: document.querySelector("#all-records"),
  contagemButton: document.querySelector("#contagem-only"),
};

const highlightPattern = /(contagem|3118601|311860|munic[ií]pios?|secretarias municipais?)/gi;

function addHighlightedText(container, value) {
  const text = String(value || "");
  let last = 0;
  for (const match of text.matchAll(highlightPattern)) {
    container.append(document.createTextNode(text.slice(last, match.index)));
    const mark = document.createElement("mark");
    mark.textContent = match[0];
    container.append(mark);
    last = match.index + match[0].length;
  }
  container.append(document.createTextNode(text.slice(last)));
}

function addBadge(parent, text, className = "") {
  const badge = document.createElement("span");
  badge.className = `badge ${className}`.trim();
  badge.textContent = text;
  parent.append(badge);
}

function metadata(label, value) {
  const span = document.createElement("span");
  span.textContent = `${label}: ${value || "—"}`;
  return span;
}

function createRecord(item) {
  const article = document.createElement("article");
  article.className = "record";
  article.dataset.relevance = item.relevance || "baixa";

  const badges = document.createElement("div");
  badges.className = "record-top";
  addBadge(badges, item.source || "Fonte não informada");
  addBadge(badges, item.type || "outros");
  const relevanceClass = (item.relevance || "baixa").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  addBadge(badges, `Relevância ${item.relevance || "baixa"}`, `relevance-${relevanceClass}`);
  for (const theme of item.theme || []) addBadge(badges, theme);

  const title = document.createElement("h2");
  title.textContent = `${item.number || "Ato"} · ${item.title || item.ementa || "Sem título"}`;

  const ementa = document.createElement("p");
  ementa.className = "ementa";
  ementa.textContent = item.ementa || item.title || "Ementa não informada.";

  const meta = document.createElement("div");
  meta.className = "record-meta";
  meta.append(
    metadata("Órgão", item.agency),
    metadata("Data", item.date),
    metadata("Valor", item.value),
    metadata("Prazo/vigência", item.deadline),
  );
  if ((item.municipal_mentions || []).length) {
    meta.append(metadata("Menções municipais", item.municipal_mentions.join(", ")));
  }

  const excerpt = document.createElement("p");
  excerpt.className = "excerpt";
  addHighlightedText(excerpt, item.snippet || "");

  const link = document.createElement("a");
  let validLink = false;
  try {
    const url = new URL(item.url, window.location.href);
    validLink = url.protocol === "https:" || url.protocol === "http:";
    if (validLink) link.href = url.href;
  } catch {
    validLink = false;
  }
  if (validLink) {
    link.className = "record-link";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Consultar publicação original ↗";
  }

  article.append(badges, title, ementa, meta, excerpt);
  if (validLink) article.append(link);
  return article;
}

function fillOptions(select, values) {
  const sorted = [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  for (const value of sorted) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function render() {
  const query = elements.search.value.trim().toLocaleLowerCase("pt-BR");
  const filtered = state.records.filter((item) => {
    const matchesText = !query || [
      item.title, item.ementa, item.snippet, item.agency, item.type,
      ...(item.theme || []), ...(item.municipal_mentions || []),
    ].join(" ").toLocaleLowerCase("pt-BR").includes(query);
    const matchesContagem = !state.contagemOnly || item.relevance === "alta";
    const matchesDate = (!elements.from.value || item.date >= elements.from.value)
      && (!elements.to.value || item.date <= elements.to.value);
    return matchesText
      && matchesContagem
      && matchesDate
      && (!elements.source.value || item.source === elements.source.value)
      && (!elements.type.value || item.type === elements.type.value)
      && (!elements.relevance.value || item.relevance === elements.relevance.value);
  });

  elements.records.replaceChildren(...filtered.map(createRecord));
  elements.empty.hidden = filtered.length !== 0;
  elements.resultCount.textContent = `${filtered.length} de ${state.records.length} atos`;
  elements.allButton.classList.toggle("active", !state.contagemOnly);
  elements.allButton.setAttribute("aria-pressed", String(!state.contagemOnly));
  elements.contagemButton.classList.toggle("active", state.contagemOnly);
  elements.contagemButton.setAttribute("aria-pressed", String(state.contagemOnly));
}

async function load() {
  try {
    const response = await fetch("data.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`data.json retornou HTTP ${response.status}`);
    const data = await response.json();
    state.records = Array.isArray(data.records) ? data.records : [];
    elements.recordCount.textContent = `${state.records.length} atos monitorados`;
    elements.updated.textContent = data.updated_at
      ? `Atualizado em ${new Date(data.updated_at).toLocaleString("pt-BR")}`
      : "Aguardando a primeira coleta automática.";
    fillOptions(elements.source, state.records.map((item) => item.source));
    fillOptions(elements.type, state.records.map((item) => item.type));
    render();
  } catch (error) {
    elements.recordCount.textContent = "Não foi possível carregar as publicações";
    elements.updated.textContent = error.message;
    elements.empty.hidden = false;
  }
}

for (const control of [elements.search, elements.source, elements.type, elements.relevance, elements.from, elements.to]) {
  control.addEventListener("input", render);
  control.addEventListener("change", render);
}
elements.allButton.addEventListener("click", () => { state.contagemOnly = false; render(); });
elements.contagemButton.addEventListener("click", () => { state.contagemOnly = true; render(); });
load();
