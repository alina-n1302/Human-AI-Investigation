export function prettyHyp(h) {
  if (!h) return "No leading hypothesis";
  if (h === "inconclusive") return "Inconclusive \u2014 more evidence needed";

  return h
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function prettyAbstainReason(reason) {
  if (reason === "insufficient_evidence") {
    return "no hypothesis reached even minimal evidence support";
  }
  if (reason === "too_close_to_call") {
    return "the leading hypotheses are too close together to call";
  }
  return "the evidence does not clearly favor one hypothesis";
}

export function scoreClass(score, max) {
  if (score >= max * 0.66) return "score-hot";
  if (score >= max * 0.33) return "score-warm";
  return "score-cool";
}

export function shortHash(hash) {
  if (!hash) return "";
  return `${hash.slice(0, 8)}…${hash.slice(-4)}`;
}
