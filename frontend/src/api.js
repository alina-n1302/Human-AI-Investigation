const API = "/api";

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Request failed: ${url}`);
  return res.json();
}

export const getCases = () => fetchJSON(`${API}/cases`);

export const getHypothesisTypes = () => fetchJSON(`${API}/hypotheses`);

export const getHypothesisModel = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/hypothesis-model`);

export const getBaseline = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/baseline`);

export const getMlRank = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/ml-rank`);

export const getTimeline = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/timeline`);

export const getEventGraph = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/event-graph`);

export const getHypotheses = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/hypotheses`);

export const getRobustness = (caseId) =>
  fetchJSON(`${API}/cases/${caseId}/robustness`);

export const getDecisions = () => fetchJSON(`${API}/decisions`);

export const getAuditIntegrity = () => fetchJSON(`${API}/decisions/verify`);

export const recordDecision = (payload) =>
  fetchJSON(`${API}/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export async function uploadCase(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API}/cases/upload`, {
    method: "POST",
    body: formData,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || "upload failed");
  return body;
}

export async function loadCaseBundle(caseId) {
  const [
    baseline,
    mlRank,
    timelineData,
    eventGraph,
    hyp,
    robustness,
    hypothesisModel,
  ] = await Promise.all([
    getBaseline(caseId),
    getMlRank(caseId),
    getTimeline(caseId),
    getEventGraph(caseId),
    getHypotheses(caseId),
    getRobustness(caseId),
    getHypothesisModel(caseId).catch(() => null),
  ]);
  return {
    baseline,
    mlRank,
    timelineData,
    eventGraph,
    hyp,
    robustness,
    hypothesisModel,
  };
}
