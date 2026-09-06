import React, { useEffect, useState, useCallback } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Tabs from "./components/Tabs.jsx";
import EvidencePanel from "./components/EvidencePanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import HypothesesPanel from "./components/HypothesesPanel.jsx";
import RobustnessPanel from "./components/RobustnessPanel.jsx";
import DecisionPanel from "./components/DecisionPanel.jsx";
import {
  getCases,
  getDecisions,
  getAuditIntegrity,
  getHypothesisTypes,
  loadCaseBundle,
  uploadCase,
} from "./api.js";

export default function App() {
  const [cases, setCases] = useState([]);
  const [hypothesisTypes, setHypothesisTypes] = useState([]);
  const [currentCaseId, setCurrentCaseId] = useState(null);
  const [activeTab, setActiveTab] = useState("evidence");
  const [investigatorName, setInvestigatorName] = useState("demo_investigator");
  const [decisions, setDecisions] = useState([]);
  const [integrity, setIntegrity] = useState(null);
  const [bundle, setBundle] = useState(null);
  const [caseLoadedAt, setCaseLoadedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshAuditLog = useCallback(async () => {
    const [d, chain] = await Promise.all([
      getDecisions(),
      getAuditIntegrity().catch(() => null),
    ]);
    setDecisions(d);
    setIntegrity(chain);
  }, []);

  const loadCase = useCallback(async (caseId) => {
    setLoading(true);
    try {
      const data = await loadCaseBundle(caseId);
      setBundle(data);
      setCurrentCaseId(caseId);
      setCaseLoadedAt(Date.now());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleUploadCase = useCallback(
    async (file) => {
      const { case_id } = await uploadCase(file);
      const caseList = await getCases();
      setCases(caseList);
      await loadCase(case_id);
    },
    [loadCase],
  );

  useEffect(() => {
    (async () => {
      try {
        const [caseList, hypTypes] = await Promise.all([
          getCases(),
          getHypothesisTypes(),
        ]);
        setCases(caseList);
        setHypothesisTypes(hypTypes);
        if (caseList.length > 0) {
          await loadCase(caseList[0].case_id);
        }
        await refreshAuditLog();
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    })();
  }, []);

  const scenario =
    cases.find((c) => c.case_id === currentCaseId)?.scenario || "";

  if (error) {
    return (
      <div className="frame">
        <main className="main">
          <p className="rail-note">Could not reach the API: {error}</p>
        </main>
      </div>
    );
  }

  return (
    <div className="frame">
      <Sidebar
        cases={cases}
        currentCaseId={currentCaseId}
        onCaseChange={loadCase}
        scenario={scenario}
        investigatorName={investigatorName}
        onInvestigatorNameChange={setInvestigatorName}
        decisions={decisions}
        integrity={integrity}
        onUploadCase={handleUploadCase}
      />

      <main className="main">
        <Tabs active={activeTab} onChange={setActiveTab} />

        {loading || !bundle ? (
          <p className="rail-note">Loading case data&hellip;</p>
        ) : (
          <>
            {activeTab === "evidence" && (
              <EvidencePanel
                baseline={bundle.baseline}
                mlRank={bundle.mlRank}
              />
            )}
            {activeTab === "timeline" && (
              <TimelinePanel
                data={bundle.timelineData}
                eventGraph={bundle.eventGraph}
              />
            )}
            {activeTab === "hypotheses" && (
              <HypothesesPanel
                result={bundle.hyp}
                hypothesisModel={bundle.hypothesisModel}
              />
            )}
            {activeTab === "robustness" && (
              <RobustnessPanel report={bundle.robustness} />
            )}
            {activeTab === "decision" && (
              <DecisionPanel
                caseId={currentCaseId}
                investigatorName={investigatorName}
                hypothesisTypes={hypothesisTypes}
                caseLoadedAt={caseLoadedAt}
                onDecisionRecorded={refreshAuditLog}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
