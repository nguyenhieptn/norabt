import React from "react";
import BotDetailView from "./BotDetailView.jsx";

/**
 * The portfolio report.
 *
 * Deliberately a thin wrapper around BotDetailView rather than a view of its
 * own. A multi-bot run does not produce several reports plus a summary panel;
 * it produces ONE report whose subject is the members' merged book, built by
 * the same backend renderer, carrying the same three tabs and the same
 * stylesheet as a single bot's. The only difference is a diversification
 * section the server injects into that document.
 *
 * An earlier version of this file rebuilt the whole report in React. That
 * guaranteed the two pages would drift -- every chart, badge and table would
 * have had to be reimplemented and then kept in step with the server's -- and
 * it is exactly what routing through BotDetailView avoids.
 *
 * `portfolioId` is a PORT_… digest of the member set, produced by the backend
 * and shown in place of a bot code.
 */
export default function PortfolioDetailView({ portfolioId, onBack, onOpenBot, onReanalyze = null, isUser = false }) {
  if (!portfolioId) {
    return (
      <div className="report-spa-error">
        <div className="spa-error-title">No portfolio selected</div>
        <p className="spa-error-desc">
          Run a portfolio analysis from the search box, or open one from the
          portfolio history.
        </p>
        {onBack && (
          <div className="btn-row" style={{ justifyContent: "center", marginTop: 16 }}>
            <button type="button" className="btn" onClick={onBack}>
              ← Back
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <BotDetailView
      code={portfolioId}
      // Nạp qua `/api/...` chứ không phải `/portfolio/...`: vhost nginx của
      // môi trường này kết bằng `location / { return 404; }`, nên mọi tuyến
      // Starlette mới cần một `location` tương ứng, còn mọi thứ dưới `/api/`
      // thì đã được proxy sẵn. Hai đường trỏ về CÙNG một handler, nên đây
      // không phải bản sao thứ hai của trang. `/portfolio/<id>` vẫn là URL
      // chia sẻ chính thức và là thứ `report_url` phát ra.
      reportPath={`/api/portfolio/page/${encodeURIComponent(portfolioId)}`}
      onBack={onBack}
      backLabel={isUser ? null : "Back to portfolio runs"}
      onReanalyze={isUser || !onReanalyze ? null : () => onReanalyze(portfolioId)}
      onOpenBot={onOpenBot}
      isUser={isUser}
    />
  );
}
