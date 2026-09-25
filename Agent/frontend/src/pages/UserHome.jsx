import React from "react";
import { useSearchParams } from "react-router-dom";
import AnalyzeFlow from "../components/AnalyzeFlow.jsx";
import BotDetailView from "../components/BotDetailView.jsx";
import PortfolioDetailView from "../components/PortfolioDetailView.jsx";
import { Block } from "../components/common.jsx";

/** "/user" -- role `user`'s screen:
 * - Single view input: nhập 1 ID chạy đơn, nhập nhiều ID chạy tổ hợp
 * - Báo cáo đơn lẻ (BotDetailView) khi phân tích 1 bot
 * - Báo cáo tổ hợp (PortfolioDetailView) khi phân tích nhiều bot
 */
export default function UserHome() {
  const [searchParams, setSearchParams] = useSearchParams();
  const botCode =
    searchParams.get("code") ||
    searchParams.get("bot_code") ||
    searchParams.get("id_bot") ||
    searchParams.get("botId") ||
    searchParams.get("uniqueCode") ||
    searchParams.get("unique_code");
  const portfolioId = searchParams.get("id") || searchParams.get("portfolio_id");

  if (botCode) {
    return (
      <div className="page user-page">
        <BotDetailView
          code={botCode}
          onBack={searchParams.get("from") === "search" ? () => setSearchParams({}) : undefined}
          isUser={true}
        />
      </div>
    );
  }

  // Điều kiện đọc thẳng từ thứ màn hình này thực sự cần để render: một id tổ
  // hợp trên URL. Biến `currentTab` cũ đã bị bỏ khi `botCode` chuyển sang dò
  // nhiều tham số, nên nhánh này từng ném ReferenceError mọi lần `botCode`
  // rỗng. Không còn giữ payload trong state: trang tự nạp từ `/portfolio/<id>`,
  // vốn đã được ghi xuống đĩa TRƯỚC khi `analyze_portfolio` trả về, nên bản
  // sao trong bộ nhớ chỉ là một nguồn sự thật thứ hai chờ lệch pha.
  if (portfolioId) {
    return (
      <div className="page">
        <PortfolioDetailView
          portfolioId={portfolioId}
          onBack={() => setSearchParams({})}
          onOpenBot={(c) => setSearchParams({ tab: "bot", code: c })}
          isUser={true}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="head" style={{ marginBottom: "20px" }}>
        <div className="crumb">MONITORING SYSTEM · QUANTITATIVE RISK TOOL</div>
        <div className="head-row">
          <h1>Look Up &amp; Analyze Bot Risk</h1>
        </div>
        <p>
          Enter an OKX bot identifier (uniqueCode) to run a multi-dimensional risk assessment and Monte Carlo simulation. Enter one bot, or multiple bots (comma- or space-separated) to measure portfolio correlation.
        </p>
      </div>

      <Block
        title="Direct Quantitative Assessment from OKX"
        note="Monte Carlo Engine &amp; Portfolio Correlation Assessment"
      >
        <AnalyzeFlow
          onOpenBot={(targetCode) => setSearchParams({ tab: "bot", code: targetCode, from: "search" })}
          onOpenPortfolio={(targetId) =>
            setSearchParams({ tab: "portfolio", id: targetId })
          }
        />
      </Block>
    </div>
  );
}
