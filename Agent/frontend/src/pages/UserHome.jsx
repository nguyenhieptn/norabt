import React from "react";
import { useSearchParams } from "react-router-dom";
import AnalyzeFlow from "../components/AnalyzeFlow.jsx";
import BotDetailView from "../components/BotDetailView.jsx";
import { Block } from "../components/common.jsx";

/** "/user" -- role `user`'s only screen: the shared two-step lookup ->
 * confirm -> analyze flow, nothing else (task's own spec for this role).
 */
export default function UserHome() {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get("tab");
  const code = searchParams.get("code");

  if (currentTab === "bot" && code) {
    return (
      <div className="page">
        <BotDetailView
          code={code}
          onBack={() => setSearchParams({})}
          isUser={true}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="head" style={{ marginBottom: "20px" }}>
        <div className="crumb">MONITORING SYSTEM · ASSESSMENT TOOL</div>
        <div className="head-row">
          <h1>Look up &amp; analyze a new bot</h1>
        </div>
        <p>
          Enter a bot's OKX identifier (uniqueCode) for instant assessment with a multi-dimensional risk model and Monte Carlo simulation.
        </p>
      </div>

      <Block
        title="Live assessment directly from OKX"
        note="Monte Carlo engine &amp; risk assessment"
      >
        <AnalyzeFlow onOpenBot={(targetCode) => setSearchParams({ tab: "bot", code: targetCode })} />
      </Block>
    </div>
  );
}
