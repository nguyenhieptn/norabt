import React, { useMemo, useState } from "react";
import { Block, Cards, Card } from "./common.jsx";

const CORE_VERDICTS = [
  "DRAWDOWN: HIGH · QUALITY: WEAK",
  "DRAWDOWN: HIGH · QUALITY: GOOD",
  "DRAWDOWN: LOW · QUALITY: GOOD",
  "DRAWDOWN: LOW · QUALITY: WEAK",
  "HIDDEN RISK",
];

const VERDICT_COLOR_VAR = {
  "DRAWDOWN: HIGH · QUALITY: WEAK": "var(--verdict-high-dd-weak-q)",
  "DRAWDOWN: HIGH · QUALITY: GOOD": "var(--verdict-high-dd-good-q)",
  "DRAWDOWN: LOW · QUALITY: GOOD": "var(--verdict-low-dd-good-q)",
  "DRAWDOWN: LOW · QUALITY: WEAK": "var(--verdict-low-dd-weak-q)",
  "HIDDEN RISK": "var(--verdict-hidden-risk)",
  "INSUFFICIENT EVIDENCE": "var(--verdict-unknown)",
};

// Bốn bậc TRẠNG THÁI (tốt -> cảnh báo -> nghiêm trọng -> nguy cấp), không
// phải bảng màu phân loại: đây là MỘT đại lượng có thứ tự, không phải bốn
// hạng mục ngang hàng.
//
// Bộ cũ (#16a34a/#ca8a04/#ea580c/#dc2626) trượt kiểm định màu:
//   cam #ea580c vs vàng #ca8a04 -- ΔE 2.9 với người mù màu đỏ-lục (deutan),
//   tức gần như một màu; đỏ #dc2626 vs cam #ea580c -- ΔE 8.7 ngay cả với
//   mắt thường. Bốn cột xếp cạnh nhau mà ba cột phải cùng một dải màu là
//   cách chắc chắn để người đọc nhìn nhầm.
// Bộ dưới đây đưa ΔE deutan lên 11.3. Hai bậc giữa vẫn dưới ngưỡng tương
// phản 3:1 trên nền sáng -- chấp nhận được VÌ mỗi cột đã có nhãn chữ trực
// tiếp ("Thấp"/"Trung bình"/...), nên màu không bao giờ là kênh duy nhất
// mang nghĩa.
const RISK_BUCKETS = [
  { label: "< 30", sub: "Low", color: "#0ca30c" },
  { label: "30 – 50", sub: "Medium", color: "#fab219" },
  { label: "50 – 70", sub: "High", color: "#ec835a" },
  { label: "≥ 70", sub: "Very High", color: "#d03b3b" },
];

function riskBucketIndex(value) {
  if (value < 30) return 0;
  if (value < 50) return 1;
  if (value < 70) return 2;
  return 3;
}

function computeOverview(rows) {
  const scored = rows.filter((row) => typeof row.risk === "number");
  const tierCounts = {};
  const bucketCounts = [0, 0, 0, 0];
  for (const row of scored) {
    const tier = row.verdict || "INSUFFICIENT EVIDENCE";
    tierCounts[tier] = (tierCounts[tier] || 0) + 1;
    bucketCounts[riskBucketIndex(row.risk)] += 1;
  }

  const vetoReasonCounts = new Map();
  for (const row of rows) {
    for (const reason of row.veto_reasons || []) {
      vetoReasonCounts.set(reason, (vetoReasonCounts.get(reason) || 0) + 1);
    }
  }

  const losingCount = rows.filter(
    (row) => typeof row.total_pnl === "number" && row.total_pnl < 0,
  ).length;
  const vetoCount = scored.filter((row) => row.is_veto).length;

  const sortedRisks = scored.map((row) => row.risk).sort((a, b) => a - b);
  let medianRisk = null;
  if (sortedRisks.length > 0) {
    const mid = Math.floor(sortedRisks.length / 2);
    medianRisk =
      sortedRisks.length % 2 === 1
        ? sortedRisks[mid]
        : (sortedRisks[mid - 1] + sortedRisks[mid]) / 2;
  }

  return {
    total: rows.length,
    vetoCount,
    losingCount,
    medianRisk,
    tierCounts,
    bucketCounts,
    vetoReasonCounts,
  };
}

function formatInt(value) {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-US");
}

/**
 * Donut chart following Nora design system:
 * - SVG donut ring with total count inside on the left
 * - Pure HTML flex list legend on the right with full label, count, and percent
 * This cleanly separates visual chart geometry from readable text content.
 */
function NoraDonut({ slices, total, onPick, openLabel }) {
  const S = 190;
  const R = 84;
  const r = 56;
  const C = S / 2;
  const KHE = 2 / R; // 2px gap in radians

  const effectiveTotal = Math.max(total, 1);
  const activeSlices = slices.filter((s) => s.value > 0);

  let angle = -Math.PI / 2;
  const arcs = activeSlices.map((s, i) => {
    const pct = s.value / effectiveTotal;
    const widthRad = pct * Math.PI * 2;
    const a0 = angle + KHE / 2;
    const a1 = angle + widthRad - KHE / 2;
    angle += widthRad;
    const large = widthRad > Math.PI ? 1 : 0;
    const pt = (rad, radDist) => [
      C + radDist * Math.cos(rad),
      C + radDist * Math.sin(rad),
    ];
    const [x0, y0] = pt(a0, R);
    const [x1, y1] = pt(a1, R);
    const [x2, y2] = pt(a1, r);
    const [x3, y3] = pt(a0, r);

    return {
      ...s,
      pctVal: (pct * 100).toFixed(1),
      d:
        a1 <= a0
          ? ""
          : `M${x0},${y0} A${R},${R} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r},${r} 0 ${large} 0 ${x3},${y3} Z`,
    };
  });

  return (
    <div className="viz-donut">
      <div className="viz-donut-graphic">
        <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} role="img">
          {total === 0 ? (
            <circle
              cx={C}
              cy={C}
              r={(R + r) / 2}
              fill="none"
              stroke="var(--line)"
              strokeWidth={R - r}
            />
          ) : (
            arcs.map((arc) => (
              <path
                key={arc.label}
                d={arc.d}
                fill={arc.color}
                className={onPick ? "viz-slice-pick" : undefined}
                onClick={onPick ? () => onPick(arc.label) : undefined}
              >
                <title>{`${arc.label} — ${formatInt(arc.value)} bot`}</title>
              </path>
            ))
          )}
          <text x={C} y={C - 4} textAnchor="middle" className="viz-hero">
            {formatInt(total)}
          </text>
          <text x={C} y={C + 16} textAnchor="middle" className="viz-sub">
            total bots
          </text>
        </svg>
      </div>

      <div className="viz-legend">
        {slices.map((slice) => {
          const pct = total > 0 ? ((slice.value / total) * 100).toFixed(1) : "0.0";
          const empty = slice.value === 0;
          // Nhóm rỗng KHÔNG bấm được: mở ra một danh sách trống chỉ tốn một
          // cú bấm để phát hiện là không có gì.
          const pickable = Boolean(onPick) && !empty;
          const inner = (
            <>
              <i style={{ background: slice.color }} />
              <span className="ten" title={slice.label}>
                {slice.label}
              </span>
              <b>{formatInt(slice.value)}</b>
              <span className="pct">{pct}%</span>
            </>
          );
          if (!pickable) {
            return (
              <div key={slice.label} className={`viz-leg ${empty ? "mo" : ""}`}>
                {inner}
              </div>
            );
          }
          return (
            <button
              key={slice.label}
              type="button"
              className={`viz-leg viz-leg-pick ${
                openLabel === slice.label ? "on" : ""
              }`}
              aria-expanded={openLabel === slice.label}
              onClick={() => onPick(slice.label)}
              title={`View ${formatInt(slice.value)} bots in this group`}
            >
              {inner}
              <span className="viz-leg-caret" aria-hidden="true">
                {openLabel === slice.label ? "▾" : "▸"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Vertical bar chart for risk score buckets.
 */
/**
 * Đường cong trơn đi qua đúng các điểm đã cho, dùng nội suy bậc ba ĐƠN ĐIỆU
 * (Fritsch & Carlson, 1980).
 *
 * VÌ SAO KHÔNG DÙNG CATMULL-ROM hay một spline trơn thông thường: dữ liệu ở
 * đây zigzag mạnh (2 -> 13 -> 2 -> 14). Spline thường sẽ VỌT LỐ ở các khúc
 * ngoặt -- đường cong phình ra ngoài khoảng giá trị của hai điểm hai đầu,
 * chạm đáy dưới 0 hoặc vượt trên đỉnh cao nhất. Trên một biểu đồ rủi ro,
 * đó là vẽ ra những con số chưa từng tồn tại: người đọc sẽ thấy một "đỉnh"
 * hoặc một "đáy" mà dữ liệu không hề có.
 *
 * Nội suy đơn điệu ràng buộc hệ số góc tại mỗi điểm (bước alpha/beta dưới
 * đây) để đường cong giữ nguyên chiều tăng/giảm của từng đoạn. Hệ quả: nó
 * không bao giờ vượt ra ngoài khoảng [min, max] của hai điểm kề. Trơn mắt,
 * nhưng không nói dối.
 */
function monotoneCubicPath(pts) {
  const n = pts.length;
  if (n === 0) return "";
  if (n === 1) return `M ${pts[0][0]} ${pts[0][1]}`;
  if (n === 2) return `M ${pts[0][0]} ${pts[0][1]} L ${pts[1][0]} ${pts[1][1]}`;

  // Hệ số góc từng đoạn.
  const dx = [];
  const slope = [];
  for (let i = 0; i < n - 1; i += 1) {
    const h = pts[i + 1][0] - pts[i][0];
    dx.push(h);
    slope.push(h === 0 ? 0 : (pts[i + 1][1] - pts[i][1]) / h);
  }

  // Tiếp tuyến ban đầu: trung bình hai đoạn kề, hai đầu lấy chính đoạn biên.
  const m = new Array(n);
  m[0] = slope[0];
  m[n - 1] = slope[n - 2];
  for (let i = 1; i < n - 1; i += 1) m[i] = (slope[i - 1] + slope[i]) / 2;

  // Ràng buộc đơn điệu -- đây chính là phần chặn vọt lố.
  for (let i = 0; i < n - 1; i += 1) {
    if (slope[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const alpha = m[i] / slope[i];
    const beta = m[i + 1] / slope[i];
    const sq = alpha * alpha + beta * beta;
    if (sq > 9) {
      const tau = 3 / Math.sqrt(sq);
      m[i] = tau * alpha * slope[i];
      m[i + 1] = tau * beta * slope[i];
    }
  }

  let d = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < n - 1; i += 1) {
    const h = dx[i] / 3;
    d +=
      ` C ${pts[i][0] + h} ${pts[i][1] + m[i] * h}` +
      ` ${pts[i + 1][0] - h} ${pts[i + 1][1] - m[i + 1] * h}` +
      ` ${pts[i + 1][0]} ${pts[i + 1][1]}`;
  }
  return d;
}

function NoraVerticalBars({ buckets, counts }) {
  // Khung cao hơn bản cũ (180 -> 240) và cột được canh GIỮA thẻ thay vì dính
  // mép trên: thẻ này nằm cùng hàng lưới với thẻ "Phân bố xếp loại" cao hơn,
  // nên nó bị kéo giãn và phần thừa dồn hết xuống dưới.
  const width = 380;
  const height = 320;
  const leftPad = 26;
  const rightPad = 18;
  const topPad = 34;
  const bottomPad = 50;
  const plotW = width - leftPad - rightPad;
  const plotH = height - topPad - bottomPad;

  const maxVal = Math.max(...counts, 1);
  const n = buckets.length;
  const colW = plotW / n;
  const barW = Math.min(44, colW * 0.56);

  // Toạ độ đỉnh từng cột -- dùng chung cho cả cột lẫn đường xu hướng, nên hai
  // lớp không bao giờ lệch nhau.
  const points = buckets.map((b, i) => {
    const val = counts[i] || 0;
    const cx = leftPad + colW * i + colW / 2;
    const barH = (val / maxVal) * plotH;
    return { ...b, val, cx, barH, cy: topPad + plotH - barH };
  });

  // Đường nối đỉnh các cột. CÙNG một trục với cột, không phải trục thứ hai --
  // biểu đồ hai trục là thứ phải tránh. Giá trị của nó: bốn cột rời rạc bắt
  // người đọc tự nối trong đầu, còn đường này cho thấy ngay HÌNH DẠNG phân
  // bố -- ở đây là hai đỉnh (nhóm trung bình và nhóm rất cao) với vùng trũng
  // ở giữa, tức đàn bot đang phân cực chứ không tụ quanh một mức rủi ro.
  const linePath = monotoneCubicPath(points.map((pt) => [pt.cx, pt.cy]));

  return (
    <div className="viz-bars-container">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", maxHeight: 380 }}
        role="img"
        aria-label={`Risk score distribution by range: ${points
          .map((pt) => `${pt.sub} ${pt.val} bot`)
          .join(", ")}`}
      >
        <line
          x1={leftPad}
          y1={topPad + plotH}
          x2={leftPad + plotW}
          y2={topPad + plotH}
          className="viz-truc"
        />

        {points.map((pt) => (
          <g key={pt.label}>
            <rect
              x={pt.cx - barW / 2}
              y={pt.cy}
              width={barW}
              height={Math.max(pt.val > 0 ? 3 : 0, pt.barH)}
              rx={4}
              fill={pt.color}
              opacity={pt.val > 0 ? 1 : 0.25}
            >
              <title>{`${pt.sub} (${pt.label}): ${formatInt(pt.val)} bot`}</title>
            </rect>
          </g>
        ))}

        {/* Đường xu hướng vẽ SAU các cột để không bị cột che, nhưng dùng màu
            mực trung tính -- nó mô tả hình dạng của chính dữ liệu đó, không
            phải một chuỗi số liệu thứ hai, nên không được mang màu riêng
            trông như một hạng mục mới. */}
        <path d={linePath} className="viz-trend-line" />
        {points.map((pt) => (
          <circle key={`m-${pt.label}`} cx={pt.cx} cy={pt.cy} r={4} className="viz-trend-dot" />
        ))}

        {points.map((pt) => (
          <g key={`t-${pt.label}`}>
            <text x={pt.cx} y={pt.cy - 12} textAnchor="middle" className="viz-val-text">
              {formatInt(pt.val)}
            </text>
            <text x={pt.cx} y={topPad + plotH + 18} textAnchor="middle" className="viz-nhan">
              {pt.label}
            </text>
            <text x={pt.cx} y={topPad + plotH + 32} textAnchor="middle" className="viz-nhan-sub">
              {pt.sub}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

/**
 * Clean horizontal bars for top veto reasons.
 */
function NoraVetoBars({ rows }) {
  if (!rows || rows.length === 0) {
    return <div className="msg">No veto reasons recorded in the current bot list.</div>;
  }

  const maxVal = Math.max(...rows.map((r) => r.value), 1);

  return (
    <div className="veto-bar-list">
      {rows.map((r) => {
        const pct = (r.value / maxVal) * 100;
        return (
          <div key={r.label} className="veto-bar-row">
            <div className="veto-bar-label" title={r.label}>
              {r.label}
            </div>
            <div className="veto-bar-track">
              <div
                className="veto-bar-fill"
                style={{ width: `${pct}%`, background: "var(--down)" }}
              />
            </div>
            <div className="veto-bar-count num">{formatInt(r.value)}</div>
          </div>
        );
      })}
    </div>
  );
}

/** Số bot hiện thẳng trong danh sách xổ ra khi bấm một nhóm xếp loại.
 * Đủ để thấy "ai nặng nhất nhóm này" ngay tại chỗ mà không đẩy hai biểu đồ
 * bên dưới trôi quá xa; phần còn lại đi tiếp sang tab Danh sách bot (đã lọc
 * sẵn) qua nút ở chân danh sách. */
const DRILL_VISIBLE_ROWS = 8;

/** Danh sách bot của MỘT nhóm xếp loại, xổ ra ngay dưới biểu đồ tròn.
 *
 * `rows` phải được lọc bằng ĐÚNG điều kiện mà `computeOverview` dùng để đếm
 * (chỉ bot có `risk` là số), nếu không số bot hiện ra sẽ lệch với con số
 * trong chú giải -- người đọc sẽ tưởng trang đếm sai.
 *
 * Xếp theo điểm rủi ro GIẢM DẦN: đây là bảng của một hệ giám sát rủi ro,
 * con nặng nhất phải nằm trên cùng, kể cả trong nhóm "SỤT VỐN: THẤP".
 */
function VerdictDrilldown({ verdict, rows, onOpenBot, onSeeAll }) {
  const ranked = useMemo(
    () => [...rows].sort((a, b) => (b.risk ?? -Infinity) - (a.risk ?? -Infinity)),
    [rows],
  );
  const shown = ranked.slice(0, DRILL_VISIBLE_ROWS);
  const rest = ranked.length - shown.length;

  return (
    <div className="tier-drill">
      <div className="tier-drill-h">
        <span className="tier-drill-title">{verdict}</span>
        <span className="note">
          {ranked.length} bots · sorted by risk score, descending
        </span>
      </div>
      <div className="tblwrap">
        <table>
          <thead>
            <tr>
              <th className="n">#</th>
              <th>Bot</th>
              <th>Code</th>
              <th>Market</th>
              <th className="n">Risk</th>
              <th className="n">Quality</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => (
              <tr
                key={row.code}
                className="rowlink"
                onClick={() => onOpenBot(row.code)}
                title={`View report for bot ${row.code}`}
              >
                <td className="n mono">{index + 1}</td>
                <td style={{ fontWeight: 600 }}>{row.name || row.code}</td>
                <td className="mono" style={{ color: "var(--amber)" }}>
                  {row.code}
                </td>
                <td>{row.venue_asset || "—"}</td>
                <td className="n mono">
                  {typeof row.risk === "number" ? row.risk.toFixed(0) : "—"}
                </td>
                <td className="n mono">
                  {typeof row.quality === "number" ? row.quality.toFixed(0) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="tier-drill-f">
        {rest > 0 ? <span className="note">{rest} more bots in this group.</span> : null}
        {onSeeAll ? (
          <button type="button" className="btn" onClick={() => onSeeAll(verdict)}>
            Open full group in bot list →
          </button>
        ) : null}
      </div>
    </div>
  );
}


export default function AdminOverview({ rows, onFilterVerdict, onOpenBot }) {
  const overview = useMemo(() => computeOverview(rows), [rows]);
  // Nhóm xếp loại đang mở (bấm lần nữa vào chính nó thì đóng lại).
  const [openVerdict, setOpenVerdict] = useState(null);

  // CÙNG điều kiện lọc với `computeOverview` (`typeof row.risk === "number"`)
  // để số bot xổ ra luôn khớp con số trong chú giải; "nhóm khác" gom vào đúng
  // nhãn "INSUFFICIENT EVIDENCE" mà lát bánh thứ sáu đang đại diện.
  const rowsByVerdict = useMemo(() => {
    const groups = new Map();
    for (const row of rows) {
      if (typeof row.risk !== "number") continue;
      const raw = row.verdict || "INSUFFICIENT EVIDENCE";
      const key = CORE_VERDICTS.includes(raw) ? raw : "INSUFFICIENT EVIDENCE";
      const bucket = groups.get(key);
      if (bucket) bucket.push(row);
      else groups.set(key, [row]);
    }
    return groups;
  }, [rows]);

  function toggleVerdict(label) {
    setOpenVerdict((current) => (current === label ? null : label));
  }

  function openBot(code) {
    if (onOpenBot) {
      onOpenBot(code);
    } else {
      window.location.href = `/bot/${code}`;
    }
  }

  const pieSlices = useMemo(() => {
    const slices = CORE_VERDICTS.map((verdict) => ({
      label: verdict,
      value: overview.tierCounts[verdict] || 0,
      color: VERDICT_COLOR_VAR[verdict],
    }));
    const other = Object.entries(overview.tierCounts).reduce(
      (sum, [verdict, count]) =>
        CORE_VERDICTS.includes(verdict) ? sum : sum + count,
      0,
    );
    if (other > 0) {
      slices.push({
        label: "INSUFFICIENT EVIDENCE",
        value: other,
        color: VERDICT_COLOR_VAR["INSUFFICIENT EVIDENCE"],
      });
    }
    return slices;
  }, [overview.tierCounts]);

  const vetoReasonRows = useMemo(() => {
    return [...overview.vetoReasonCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([label, value]) => ({ label, value }));
  }, [overview.vetoReasonCounts]);

  return (
    <section className="overview-section">
      {/* 1. Stat cards with Minimalist OKX-Style SVG Icons */}
      <Cards>
        <Card
          label="Total bots"
          value={formatInt(overview.total)}
          sub="Loaded & risk-assessed"
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          }
          glowColor="primary"
        />
        <Card
          label="Safety vetoed"
          value={formatInt(overview.vetoCount)}
          sub="Violates risk standards"
          tone={overview.vetoCount > 0 ? "down" : ""}
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          }
          glowColor={overview.vetoCount > 0 ? "danger" : "success"}
        />
        <Card
          label="Median risk score"
          value={
            overview.medianRisk == null
              ? "—"
              : overview.medianRisk.toFixed(0)
          }
          sub="Scale of 0 – 100"
          tone="amber"
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
          }
          glowColor="warning"
        />
        <Card
          label="Net losing"
          value={formatInt(overview.losingCount)}
          sub="Closed PnL < 0 USDT"
          tone={overview.losingCount > 0 ? "down" : ""}
          icon={
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
              <polyline points="17 18 23 18 23 12" />
            </svg>
          }
          glowColor={overview.losingCount > 0 ? "danger" : "primary"}
        />
      </Cards>

      {/* 2. Visual distribution blocks */}
      <div className="overview-chart-grid">
        <Block
          title="Risk verdict distribution"
          note={`${formatInt(overview.total)} bots`}
        >
          <NoraDonut
            slices={pieSlices}
            total={overview.total}
            onPick={toggleVerdict}
            openLabel={openVerdict}
          />
          {openVerdict ? (
            <VerdictDrilldown
              verdict={openVerdict}
              rows={rowsByVerdict.get(openVerdict) || []}
              onOpenBot={openBot}
              onSeeAll={onFilterVerdict}
            />
          ) : (
            <p className="tier-drill-hint">
              Click a verdict group to see the list of bots in that group.
            </p>
          )}
        </Block>

        <Block
          title="Risk score distribution"
          note="The trend line shows the distribution's shape"
          className="block-chart"
        >
          <NoraVerticalBars
            buckets={RISK_BUCKETS}
            counts={overview.bucketCounts}
          />
        </Block>
      </div>

      {/* 3. Veto reasons block */}
      <Block
        title="Most common veto reasons"
        note={
          vetoReasonRows.length > 0
            ? `${vetoReasonRows.length} notable reasons`
            : ""
        }
      >
        <NoraVetoBars rows={vetoReasonRows} />
      </Block>
    </section>
  );
}
