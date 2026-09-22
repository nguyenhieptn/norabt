import React, { useEffect, useRef, useState } from "react";
import { useSession } from "../context/SessionContext.jsx";

/**
 * Renders a server-built report document inside the SPA.
 *
 * `reportPath` exists so a PORTFOLIO can use this component unchanged. A
 * portfolio report is produced by the same backend renderer as a single bot's
 * -- its subject is just a bot merged from several ledgers -- so the two pages
 * share one stylesheet, one tab implementation, one set of charts and all of
 * the rewiring below. Building a second React view for portfolios would have
 * meant two things to keep in sync forever, and they would not have stayed in
 * sync.
 */
export default function BotDetailView({ code, reportPath, onBack, isUser = false }) {
  const { session } = useSession();
  const [htmlContent, setHtmlContent] = useState("");
  const [botMeta, setBotMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const containerRef = useRef(null);
  const reAnalyzeBtnRef = useRef(null);

  const isUserView = isUser || !session || session.role !== "admin";

  function loadReport(isRefresh = false) {
    if (!code && !reportPath) return;
    setLoading(true);
    setError(null);

    // Role scoping is decided by the server (see backend/qc/reporting/view_policy.py).
    // The SPA asks for the user-scoped document instead of deleting panels out
    // of an admin document after the fact -- stripping client-side made
    // "withheld from you" look identical to "never measured". Only actually
    // ask for it when THIS view is the user-scoped one (isUserView) -- an
    // admin opening the same component (from /#/admin) must see the full,
    // unrestricted document, not the user's trimmed one.
    const params = new URLSearchParams();
    if (isRefresh) params.set("refresh", "1");
    if (isUserView) params.set("view", "user");
    params.set("_t", String(Date.now()));
    const url = `${reportPath || `/bot/${code}`}?${params.toString()}`;
    fetch(url, { cache: "no-store", headers: { "Cache-Control": "no-cache" } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: Bot report not found`);
        return res.text();
      })
      .then((html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, "text/html");

        // 1. Trích xuất metadata cho Header đồng nhất của SPA
        const nameEl = doc.querySelector(".head-title");
        const botName = nameEl ? nameEl.textContent.trim() : code;

        const verdictEl = doc.querySelector(".verdict-badge");
        const verdict = verdictEl ? verdictEl.textContent.trim() : "";
        const verdictColor = verdictEl ? verdictEl.style.getPropertyValue("--badge-color") : "";

        const symbolEl = doc.querySelector(".venue-symbol-badge");
        const marketTag = symbolEl ? symbolEl.textContent.trim() : "";

        const snapshotEl = doc.querySelector(".snapshot-banner");
        let snapshotTime = "";
        let hasRefresh = false;
        if (snapshotEl) {
          const strong = snapshotEl.querySelector("strong");
          if (strong) {
            snapshotTime = strong.textContent.trim() + " (GMT+7)";
          } else {
            const match = snapshotEl.textContent.match(/(?:Snapshot taken at|Analysis time:|Thời gian phân tích:)\s+([^\.\-]+)/i);
            if (match) {
              snapshotTime = match[1].trim() + " (GMT+7)";
            }
          }
          hasRefresh = !!snapshotEl.querySelector('a[href*="refresh=1"]');
        }

        // 2. Dọn dẹp các thanh điều hướng rời rạc cũ từ SSR và các nút radio tab
        doc.querySelectorAll(".admin-banner, .snapshot-banner, .report-subnav-bar, .tab-nav-radio, input[name='main_tabs'], .report-header, .report-hero-card, #formula-modal, .formula-modal-backdrop").forEach((el) => el.remove());
        doc.querySelectorAll(".report-hero-identity .crumb").forEach((el) => el.remove());
        doc.querySelectorAll(".report-hero-top").forEach((el) => el.remove());
        // Unwrap .tabs-control-wrapper: giữ lại các children (.tabs-header-container, .tab-panels),
        // chỉ bỏ div bọc ngoài — xoá toàn bộ sẽ mất luôn tab bar bên trong.
        doc.querySelectorAll(".tabs-control-wrapper").forEach((wrapper) => {
          while (wrapper.firstChild) {
            wrapper.parentNode.insertBefore(wrapper.firstChild, wrapper);
          }
          wrapper.remove();
        });
        if (nameEl) nameEl.remove();

        // 3. Tab mặc định: Kích hoạt panel-report đầu tiên
        const reportPanel = doc.querySelector("#panel-report");
        if (reportPanel) {
          reportPanel.classList.add("active-tab-panel");
          reportPanel.style.display = "block";
        }
        const defaultLabel = doc.querySelector(".label-report");
        if (defaultLabel) {
          defaultLabel.classList.add("active-tab-label");
        }

        // 4. Trích xuất CSS nội bộ và thân báo cáo
        const styles = Array.from(doc.querySelectorAll("style"))
          .map((s) => s.textContent)
          .join("\n");

        // 5. Kích hoạt scripts (như METRIC_INFO, modal handlers)
        Array.from(doc.querySelectorAll("script")).forEach((s) => {
          if (s.textContent && !s.src) {
            try {
              const scriptEl = document.createElement("script");
              scriptEl.textContent = s.textContent;
              document.body.appendChild(scriptEl);
              document.body.removeChild(scriptEl);
            } catch (e) {}
          }
        });

        const main = doc.querySelector(".main");
        const bodyContent = main ? main.innerHTML : html;

        setBotMeta({
          name: botName,
          verdict,
          verdictColor,
          marketTag,
          snapshotTime,
          hasRefresh,
        });
        if (botName && botName !== code) {
          document.title = `Nora - Risk Management · ${botName}`;
        } else if (code) {
          document.title = `Nora - Risk Management · ${code}`;
        }
        setHtmlContent({ styles, bodyContent });
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Error loading report");
        setLoading(false);
      });
  }

  useEffect(() => {
    loadReport(false);
  }, [code, reportPath]);

  useEffect(() => {
    if (!containerRef.current || !htmlContent) return;

    const root = containerRef.current;

    // Chuyển tab giữa 3 thẻ: Kết quả phân tích (Analyst Result) và 2 thẻ khoá (Market, Trades)
    const tabLabels = root.querySelectorAll(".tabs-nav-bar .tab-label");
    const panels = {
      report: root.querySelector("#panel-report"),
      market: root.querySelector("#panel-market"),
      trades: root.querySelector("#panel-trades"),
    };

    tabLabels.forEach((label) => {
      label.onclick = (e) => {
        e.preventDefault();
        const forId = label.getAttribute("for");
        if (!forId) return;
        const targetTab = forId.replace("tab-nav-", "");

        Object.entries(panels).forEach(([key, panel]) => {
          if (panel) {
            if (key === targetTab) {
              panel.classList.add("active-tab-panel");
              panel.style.display = "block";
            } else {
              panel.classList.remove("active-tab-panel");
              panel.style.display = "none";
            }
          }
        });

        const radio = root.querySelector(`#${forId}`);
        if (radio) radio.checked = true;

        tabLabels.forEach((l) => l.classList.remove("active-tab-label"));
        label.classList.add("active-tab-label");
      };
    });

    // Active nhãn tab đầu tiên mặc định
    const defaultLabel = root.querySelector(".label-report");
    if (defaultLabel) defaultLabel.classList.add("active-tab-label");

    // Intercept back button clicks
    const backButtons = root.querySelectorAll(".btn-subnav-back, .back-link");
    backButtons.forEach((btn) => {
      btn.onclick = (e) => {
        e.preventDefault();
        if (onBack) onBack();
      };
    });

    // Intercept "Phân tích lại" refresh button
    const refreshBtn = root.querySelectorAll('a[href*="refresh=1"]');
    refreshBtn.forEach((btn) => {
      btn.onclick = (e) => {
        e.preventDefault();
        loadReport(true);
      };
    });

    // Intercept internal hash links (#verdict-basis-box, #trades, #market, #report, etc.)
    // Ngăn chặn đổi window.location.hash làm gãy routing của SPA HashRouter
    const hashLinks = root.querySelectorAll('a[href^="#"]');
    hashLinks.forEach((link) => {
      link.onclick = (e) => {
        e.preventDefault();
        const hash = link.getAttribute("href");
        if (!hash) return;
        const targetId = hash.slice(1);

        // Nếu là chuyển tab nội bộ (Kết quả phân tích / Thị trường chính / Lệnh & vị thế)
        if (targetId === "trades" || targetId === "market" || targetId === "report") {
          const radio = root.querySelector(`#tab-nav-${targetId}`);
          if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event("change", { bubbles: true }));
          }
          const panels = root.querySelector(".tab-panels");
          if (panels) panels.scrollIntoView({ behavior: "smooth" });
          return;
        }

        // Nếu bấm xem phương pháp luận: tự động mở bung hộp và cuộn tới
        if (targetId === "verdict-basis-box") {
          const box = root.querySelector("#verdict-basis-box");
          if (box) {
            box.classList.add("expanded");
            const pill = box.querySelector(".basis-toggle-pill");
            if (pill) pill.textContent = "Collapse ▲";
            box.scrollIntoView({ behavior: "smooth" });
          }
          return;
        }

        const targetEl = root.querySelector(`#${targetId}`);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: "smooth" });
        }
      };
    });

    // Collapsible methodology toggle
    const basisHeader = root.querySelector(".basis-header");
    if (basisHeader) {
      basisHeader.onclick = (e) => {
        e.preventDefault();
        const box = root.querySelector("#verdict-basis-box");
        if (box) {
          box.classList.toggle("expanded");
          const pill = box.querySelector(".basis-toggle-pill");
          if (pill) {
            pill.textContent = box.classList.contains("expanded")
              ? "Collapse ▲"
              : "Show methodology ▼";
          }
        }
      };
    }

    // Breadcrumb links to bots list
    const crumbLinks = root.querySelectorAll('a[href*="tab=bots"]');
    crumbLinks.forEach((link) => {
      link.onclick = (e) => {
        e.preventDefault();
        if (onBack) onBack();
      };
    });

    // Monte Carlo view tabs switcher (3 tabs: Distribution, Probability Band, Median Line)
    const mcTabBtns = root.querySelectorAll(".mc-view-tab-btn");
    const mcTabLabels = {
      dist: "📊 Distribution",
      fan: "📈 Probability Band",
      median: "📉 Median Line",
    };
    mcTabBtns.forEach((btn) => {
      const tab = btn.getAttribute("data-tab");
      if (mcTabLabels[tab]) {
        btn.innerHTML = `<span class="mc-tab-icon">${mcTabLabels[tab].slice(0, 2)}</span> ${mcTabLabels[tab].slice(3)}`;
      }
      btn.onclick = (e) => {
        e.preventDefault();
        const tabId = btn.getAttribute("data-tab");
        const panel = btn.closest(".mc-unified-panel");
        if (!panel) return;
        panel.querySelectorAll(".mc-view-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        panel.querySelectorAll(".mc-view-panel").forEach((v) => {
          if (v.getAttribute("data-view") === tabId) {
            v.style.display = "block";
            v.classList.add("active");
          } else {
            v.style.display = "none";
            v.classList.remove("active");
          }
        });
      };
    });

    // OKX-Style Table Pagination for .paginated-table
    const tables = root.querySelectorAll(".paginated-table");
    tables.forEach((table) => {
      if (table.dataset.paginationInitialized) return;
      table.dataset.paginationInitialized = "true";
      const tbody = table.querySelector("tbody");
      if (!tbody) return;
      const allRows = Array.from(tbody.querySelectorAll("tr"));
      const totalRows = allRows.length;
      const pageSize = parseInt(table.dataset.pageSize || "10", 10);
      if (totalRows <= pageSize) return;

      const totalPages = Math.ceil(totalRows / pageSize);
      let currentPage = 1;

      const pagEl = document.createElement("div");
      pagEl.className = "table-pagination";

      function renderPage(page) {
        currentPage = page;
        const start = (page - 1) * pageSize;
        const end = Math.min(start + pageSize, totalRows);

        allRows.forEach((row, idx) => {
          row.style.display = idx >= start && idx < end ? "" : "none";
        });

        pagEl.innerHTML = "";

        const infoEl = document.createElement("div");
        infoEl.className = "pagination-info";
        infoEl.textContent = `Showing ${start + 1} – ${end} of ${totalRows} trades`;

        const controlsEl = document.createElement("div");
        controlsEl.className = "pagination-controls";

        function createBtn(text, pageNum, disabled, isActive) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "pagination-btn" + (isActive ? " active" : "");
          btn.textContent = text;
          btn.disabled = !!disabled;
          if (!disabled && !isActive) {
            btn.onclick = () => renderPage(pageNum);
          }
          return btn;
        }

        controlsEl.appendChild(createBtn("«", 1, currentPage === 1));
        controlsEl.appendChild(createBtn("‹", currentPage - 1, currentPage === 1));

        let startP = Math.max(1, currentPage - 2);
        let endP = Math.min(totalPages, startP + 4);
        if (endP - startP < 4) {
          startP = Math.max(1, endP - 4);
        }

        for (let p = startP; p <= endP; p++) {
          controlsEl.appendChild(createBtn(String(p), p, false, p === currentPage));
        }

        controlsEl.appendChild(createBtn("›", currentPage + 1, currentPage === totalPages));
        controlsEl.appendChild(createBtn("»", totalPages, currentPage === totalPages));

        pagEl.appendChild(infoEl);
        pagEl.appendChild(controlsEl);
      }

      const parent = table.closest(".table-scroll") || table;
      parent.parentNode.insertBefore(pagEl, parent.nextSibling);
      renderPage(1);
    });

    // Enforce value colors & alignment for Drawdown vs. capital and Open-position audit
    // 1. Drawdown vs. capital -> Five worst losing trades SVG values
    root.querySelectorAll("#sut-giam-von svg .bar-value, .bar-chart .bar-value").forEach((el) => {
      const txt = (el.textContent || "").trim();
      if (txt.startsWith("+")) {
        el.style.setProperty("fill", "#10b981", "important");
      } else if (txt.startsWith("-") || txt.includes("-")) {
        el.style.setProperty("fill", "#ef4444", "important");
      }
    });

    // 2. Drawdown vs. capital -> Deepest drawdown episode table values
    root.querySelectorAll("#sut-giam-von table tbody tr").forEach((tr) => {
      const tds = tr.querySelectorAll("td");
      if (tds.length >= 2) {
        const valSpan = tds[1].querySelector("span") || tds[1];
        const txt = (valSpan.textContent || "").trim();
        if (txt.startsWith("+")) {
          valSpan.style.setProperty("color", "#10b981", "important");
          valSpan.style.fontWeight = "600";
        } else if (txt.startsWith("-") || txt.includes("-")) {
          valSpan.style.setProperty("color", "#ef4444", "important");
          valSpan.style.fontWeight = "600";
        }
      }
    });

    // 3. Drawdown vs. capital -> Top parameter rows
    const drawdownSec = root.querySelector("#sut-giam-von");
    if (drawdownSec) {
      drawdownSec.querySelectorAll(".param-horizontal-row").forEach((row) => {
        const valEl = row.querySelector(".param-horizontal-val");
        if (valEl) {
          const txt = (valEl.textContent || "").trim();
          if (txt.startsWith("-") || txt.includes("-")) {
            valEl.style.setProperty("color", "#ef4444", "important");
          } else if (txt.startsWith("+")) {
            valEl.style.setProperty("color", "#10b981", "important");
          }
        }
      });
    }

    // 4. Open-position audit & return distribution -> Value colors & star button vertical alignment
    const openPosSec = root.querySelector("#vi-the-mo");
    if (openPosSec) {
      openPosSec.querySelectorAll(".param-horizontal-row").forEach((row) => {
        const nameEl = row.querySelector(".param-horizontal-name");
        if (nameEl) {
          nameEl.style.setProperty("flex", "0 0 340px", "important");
          nameEl.style.setProperty("max-width", "340px", "important");
          const labelRow = nameEl.querySelector(".metric-label-row");
          if (labelRow) {
            labelRow.style.setProperty("width", "100%", "important");
            labelRow.style.setProperty("display", "flex", "important");
            labelRow.style.setProperty("justify-content", "space-between", "important");
            labelRow.style.setProperty("align-items", "center", "important");
            const starBtn = labelRow.querySelector(".formula-star-btn");
            if (starBtn) {
              starBtn.style.setProperty("margin-left", "auto", "important");
              starBtn.style.setProperty("margin-right", "4px", "important");
              starBtn.style.setProperty("flex", "0 0 16px", "important");
              starBtn.style.setProperty("width", "16px", "important");
              starBtn.style.setProperty("display", "inline-flex", "important");
              starBtn.style.setProperty("justify-content", "center", "important");
              starBtn.style.setProperty("align-items", "center", "important");
              starBtn.style.setProperty("text-align", "center", "important");
            }
          }
        }
        const valEl = row.querySelector(".param-horizontal-val");
        if (valEl) {
          const txt = (valEl.textContent || "").trim();
          if (txt.startsWith("-") || txt.includes("-")) {
            valEl.style.setProperty("color", "#ef4444", "important");
          } else {
            valEl.style.setProperty("color", "#10b981", "important");
          }
        }
      });
    }

    // 5. Statistical inference & Trade metrics tables -> star button vertical alignment
    root.querySelectorAll("#so-lieu, #suy-luan").forEach((sec) => {
      sec.querySelectorAll("table tr").forEach((tr) => {
        const td = tr.querySelector("td:first-child");
        if (td) {
          const labelRow = td.querySelector(".metric-label-row");
          if (labelRow) {
            labelRow.style.setProperty("width", "100%", "important");
            labelRow.style.setProperty("display", "flex", "important");
            labelRow.style.setProperty("justify-content", "space-between", "important");
            labelRow.style.setProperty("align-items", "center", "important");
            const starBtn = labelRow.querySelector(".formula-star-btn");
            if (starBtn) {
              starBtn.style.setProperty("margin-left", "auto", "important");
              starBtn.style.setProperty("margin-right", "4px", "important");
              starBtn.style.setProperty("flex", "0 0 16px", "important");
              starBtn.style.setProperty("width", "16px", "important");
              starBtn.style.setProperty("display", "inline-flex", "important");
              starBtn.style.setProperty("justify-content", "center", "important");
              starBtn.style.setProperty("align-items", "center", "important");
              starBtn.style.setProperty("text-align", "center", "important");
            }
          }
        }
      });
    });

    // Formula star click handler (Supports click-to-pin formula tooltip)
    root.querySelectorAll(".formula-star-btn, .formula-star").forEach((star) => {
      star.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const data = getTooltipData(star);
        if (!data || !richTip) return;

        const isCurrentlyPinned = richTip._pinnedBtn === star && richTip.classList.contains("is-visible");
        if (isCurrentlyPinned) {
          richTip.classList.remove("is-visible", "is-pinned");
          richTip._pinnedBtn = null;
          return;
        }

        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        richTip.className = isLight ? "theme-light is-visible is-pinned" : "theme-dark is-visible is-pinned";
        richTip.setAttribute("data-theme", isLight ? "light" : "dark");
        richTip._pinnedBtn = star;

        richTip.innerHTML = `
          <div class="rich-tip-header">
            <span class="rich-tip-icon">📐</span>
            <span class="rich-tip-title">${data.title || "Formula"}</span>
          </div>
          ${data.formula ? `<div class="rich-tip-formula-box"><strong class="rich-tip-formula-label">Formula:</strong> <span class="rich-tip-formula-code">${data.formula}</span></div>` : ""}
          ${data.desc ? `<div class="rich-tip-desc">${data.desc}</div>` : ""}
        `;

        const rect = star.getBoundingClientRect();
        const tipW = richTip.offsetWidth || 340;
        const tipH = richTip.offsetHeight || 120;
        let x = rect.right + 12;
        let y = rect.top;
        if (x + tipW > window.innerWidth - 10) {
          x = rect.left - tipW - 12;
        }
        if (y + tipH > window.innerHeight - 10) {
          y = Math.max(10, window.innerHeight - tipH - 12);
        }
        richTip.style.left = Math.max(10, x) + "px";
        richTip.style.top = Math.max(10, y) + "px";
      });
    });

    const handleDocClick = (e) => {
      if (richTip && richTip._pinnedBtn && !e.target.closest(".formula-star-btn, #rich-formula-tooltip")) {
        richTip.classList.remove("is-visible", "is-pinned");
        richTip._pinnedBtn = null;
      }
    };
    document.addEventListener("click", handleDocClick);

    // Rich Formula Hover Tooltips
    let richTip = document.getElementById("rich-formula-tooltip");
    if (!richTip) {
      richTip = document.createElement("div");
      richTip.id = "rich-formula-tooltip";
      document.body.appendChild(richTip);
    }

    function getTooltipData(target) {
      const el = target.closest("[data-formula], [data-metric-key], .param-label, .bar-label, .formula-star-btn");
      if (!el) return null;
      let formula = el.getAttribute("data-formula");
      const key = el.getAttribute("data-metric-key");
      let title = el.getAttribute("data-title");
      let desc = el.getAttribute("data-desc");

      if (!formula && key && window.METRIC_INFO && window.METRIC_INFO[key]) {
        const info = window.METRIC_INFO[key];
        formula = info.formula;
        title = title || info.title || key;
        desc = desc || info.desc;
      }
      if (!formula && !desc) return null;
      return { title: title || "Calculation Methodology", formula, desc };
    }

    function positionTip(e) {
      if (!richTip || richTip._pinnedBtn) return;
      const pad = 14;
      const tipW = richTip.offsetWidth || 340;
      const tipH = richTip.offsetHeight || 120;
      let x = e.clientX + pad;
      let y = e.clientY + pad;

      if (x + tipW > window.innerWidth - 10) {
        x = e.clientX - tipW - pad;
      }
      if (y + tipH > window.innerHeight - 10) {
        y = e.clientY - tipH - pad;
      }
      richTip.style.left = Math.max(10, x) + "px";
      richTip.style.top = Math.max(10, y) + "px";
    }

    const handleMouseOver = (e) => {
      if (richTip && richTip._pinnedBtn) return;
      const data = getTooltipData(e.target);
      if (!data) return;

      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      richTip.className = isLight ? "theme-light is-visible" : "theme-dark is-visible";
      richTip.setAttribute("data-theme", isLight ? "light" : "dark");

      richTip.innerHTML = `
        <div class="rich-tip-header">
          <span class="rich-tip-icon">📐</span>
          <span class="rich-tip-title">${data.title || "Formula"}</span>
        </div>
        ${data.formula ? `<div class="rich-tip-formula-box"><strong class="rich-tip-formula-label">Formula:</strong> <span class="rich-tip-formula-code">${data.formula}</span></div>` : ""}
        ${data.desc ? `<div class="rich-tip-desc">${data.desc}</div>` : ""}
      `;
      positionTip(e);
    };

    const handleMouseMove = (e) => {
      if (richTip && !richTip._pinnedBtn) {
        if (!richTip.classList.contains("is-visible")) {
          handleMouseOver(e);
        } else {
          positionTip(e);
        }
      }
    };

    const handleMouseOut = (e) => {
      if (richTip && richTip._pinnedBtn) return;
      if (
        e.relatedTarget &&
        e.relatedTarget.closest &&
        e.relatedTarget.closest(
          "[data-formula], [data-metric-key], .param-label, .bar-label, .formula-star-btn"
        )
      ) {
        return;
      }
      if (richTip) {
        richTip.classList.remove("is-visible");
      }
    };

    // Setup Nora AI Chat Widget in SPA
    const chatFab = root.querySelector("#nora-chat-fab");
    const chatWidget = root.querySelector("#nora-chat-widget");
    const chatClose = root.querySelector("#nora-chat-close");
    const chatForm = root.querySelector("#nora-chat-form");
    const chatInput = root.querySelector("#nora-chat-input");
    const chatLog = root.querySelector("#nora-chat-log");
    const chatChips = root.querySelector("#nora-chat-chips");
    const chatStatus = root.querySelector("#nora-chat-status");

    if (chatFab && chatWidget) {
      const botCode = chatWidget.getAttribute("data-bot-code") || code;
      const history = [];
      let isBusy = false;

      // Thoát HTML bằng chính DOM (gán rồi đọc lại `innerHTML`) -- không tự
      // viết regex thoát tay, để trình duyệt lo đúng MỌI ký tự đặc biệt.
      // Câu trả lời của model đi qua đây TRƯỚC khi tô đậm số liệu hay tách
      // câu, nên hai bước sau không thể mở lại một lỗ XSS nào.
      const escapeHtml = (text) => {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
      };

      // Tô đậm số liệu -- chỉ số có "%", hậu tố nhân "x", hoặc có dấu thập
      // phân mới được tô (một số nguyên trần như "212 closed trades" thì
      // không), để không tô lem nhem mọi con số trong câu.
      const METRIC_RE = /(\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%|\b\d+(?:\.\d+)?x\b|\b\d+\.\d+\b)/g;
      const highlightMetrics = (html) =>
        html.replace(METRIC_RE, '<strong class="nora-chat-metric">$1</strong>');

      // Tách câu để xuống dòng cho dễ đọc trong khung chat hẹp -- model trả
      // lời 2-6 câu liền một mạch (xem STYLE trong chat.py), dồn hết vào một
      // đoạn văn trông rất bí. Tách theo ranh giới câu: dấu kết câu + khoảng
      // trắng + MỘT CHỮ HOA ngay sau -- điều kiện "chữ hoa ngay sau" cố ý để
      // KHÔNG cắt nhầm vào số thập phân kiểu "57.08%" (sau dấu "." ở đó là
      // chữ số "08", không phải chữ hoa, nên không khớp).
      const SENTENCE_SPLIT_RE = /(?<=[.!?])\s+(?=[A-Z])/;
      const formatAnswer = (text) => {
        const sentences = text
          .split(SENTENCE_SPLIT_RE)
          .map((s) => s.trim())
          .filter(Boolean);
        return sentences.map((s) => highlightMetrics(escapeHtml(s))).join("<br><br>");
      };

      const addMsg = (role, text) => {
        if (!chatLog) return;
        const row = document.createElement("div");
        row.className = `nora-chat-msg-row msg-${role}`;
        if (role === "assistant") {
          const av = document.createElement("div");
          av.className = "nora-chat-avatar";
          row.appendChild(av);
        }
        const bubble = document.createElement("div");
        bubble.className = `nora-chat-bubble role-${role}`;
        if (role === "assistant") {
          // CHỈ vai assistant được định dạng -- câu hỏi của người dùng và
          // câu lỗi giữ `textContent` thuần, không cần tô/tách câu.
          bubble.innerHTML = formatAnswer(text);
        } else {
          bubble.textContent = text;
        }
        row.appendChild(bubble);
        chatLog.appendChild(row);
        chatLog.scrollTop = chatLog.scrollHeight;
      };

      const setChips = (questions) => {
        if (!chatChips) return;
        chatChips.innerHTML = "";
        (questions || []).forEach((q) => {
          if (!q) return;
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "nora-chat-chip";
          chip.textContent = q;
          chip.onclick = () => askQuestion(q);
          chatChips.appendChild(chip);
        });
      };

      const setBusy = (busy) => {
        isBusy = busy;
        if (chatInput) chatInput.disabled = busy;
        const sendBtn = root.querySelector("#nora-chat-send");
        if (sendBtn) sendBtn.disabled = busy;
        if (chatStatus) {
          chatStatus.innerHTML = busy
            ? '<div class="nora-chat-typing"><span class="tdot"></span><span class="tdot"></span><span class="tdot"></span><span style="margin-left:6px;font-size:11.5px;color:var(--ink-3);">Nora AI is thinking...</span></div>'
            : '';
        }
        if (chatLog) chatLog.scrollTop = chatLog.scrollHeight;
      };

      const askQuestion = async (q) => {
        q = (q || "").trim();
        if (!q || isBusy) return;
        addMsg("user", q);
        history.push({ role: "user", text: q });
        if (history.length > 6) history.splice(0, history.length - 6);
        if (chatInput) chatInput.value = "";
        setChips([]);
        setBusy(true);

        try {
          const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: botCode, question: q, history }),
          });
          const data = await resp.json();
          setBusy(false);
          if (resp.ok && data && typeof data.answer === "string") {
            addMsg("assistant", data.answer);
            history.push({ role: "assistant", text: data.answer });
            if (history.length > 6) history.splice(0, history.length - 6);
            // CỐ TÌNH không gọi lại `setChips(data.suggested_questions)`
            // nữa: gợi ý chỉ hiện MỘT LẦN lúc mở panel (trong `openChat`),
            // trước khi có tin nhắn nào -- gọi lại ở đây từng khiến gợi ý
            // biến mất lúc đang chờ (`setChips([])` trong `askQuestion`)
            // rồi HIỆN LẠI ngay khi có câu trả lời, đúng lỗi đã báo (23/09).
            // `data.suggested_questions` vẫn về từ server như cũ -- chỉ
            // phía hiển thị này không dùng tới sau lượt hỏi đầu tiên.
          } else {
            addMsg("error", (data && data.message) || "Something went wrong. Please try again.");
          }
        } catch (err) {
          setBusy(false);
          addMsg("error", "Could not reach server. Please try again.");
        }
      };

      const openChat = () => {
        chatWidget.hidden = false;
        chatWidget.removeAttribute("hidden");
        chatWidget.style.display = "flex";
        chatWidget.setAttribute("aria-hidden", "false");
        chatFab.setAttribute("aria-expanded", "true");
        if (chatLog && !chatLog.childElementCount) {
          addMsg(
            "assistant",
            "Hello! I am Nora AI risk assistant. Ask me anything about this bot's risk rating, Monte Carlo stress tests, drawdowns, or classification verdict."
          );
          setChips([
            "What does the Risk Score measure?",
            "Why did this bot get warned or vetoed?",
            "Explain the verdict and Monte Carlo tests",
            "Is this bot vulnerable to slippage or illiquidity?"
          ]);
        }
        if (chatInput) chatInput.focus();
      };

      const closeChat = () => {
        chatWidget.hidden = true;
        chatWidget.setAttribute("hidden", "");
        chatWidget.style.display = "none";
        chatWidget.setAttribute("aria-hidden", "true");
        chatFab.setAttribute("aria-expanded", "false");
        chatFab.focus();
      };

      chatFab.onclick = (e) => {
        e.preventDefault();
        if (chatWidget.hidden || chatWidget.style.display === "none") {
          openChat();
        } else {
          closeChat();
        }
      };

      if (chatClose) {
        chatClose.onclick = (e) => {
          e.preventDefault();
          closeChat();
        };
      }

      if (chatForm) {
        chatForm.onsubmit = (e) => {
          e.preventDefault();
          askQuestion(chatInput ? chatInput.value : "");
        };
      }
    }

    root.addEventListener("mouseover", handleMouseOver);
    root.addEventListener("mousemove", handleMouseMove);
    root.addEventListener("mouseout", handleMouseOut);

    return () => {
      root.removeEventListener("mouseover", handleMouseOver);
      root.removeEventListener("mousemove", handleMouseMove);
      root.removeEventListener("mouseout", handleMouseOut);
      document.removeEventListener("click", handleDocClick);
      if (richTip) {
        richTip.classList.remove("is-visible", "is-pinned");
        richTip._pinnedBtn = null;
      }
    };
  }, [htmlContent, onBack]);

  if (loading) {
    return (
      <div className="report-spa-loading">
        <div className="spa-loading-spinner" />
        <div className="spa-loading-text">
          Loading quantitative report data for <strong>{code}</strong>...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="report-spa-error">
        <div className="spa-error-title">Could not load report</div>
        <p className="spa-error-desc">{error}</p>
        <div className="btn-row" style={{ justifyContent: "center", marginTop: 16 }}>
          <button type="button" className="btn pri" onClick={() => loadReport(false)}>
            🔄 Retry loading report
          </button>
          {onBack && (
            <button type="button" className="btn" onClick={onBack}>
              ← {isUserView ? "Look up a different bot" : "Back to bot list"}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="bot-report-spa-container" ref={containerRef}>
      {/* HEADER ĐỒNG NHẤT 100% VỚI HỆ THỐNG GIAO DIỆN CHUNG */}
      {botMeta && (
        <div className="head report-unified-head">
          <div className="crumb">MONITORING SYSTEM · DETAILED QUANTITATIVE PROFILE</div>
          <div className="head-row report-head-row">
            {(onBack || (!isUserView && botMeta.hasRefresh)) && (
              <>
                <div className="head-actions report-head-actions-left">
                  {onBack && (
                    <button
                      type="button"
                      className="btn btn-subnav-back"
                      onClick={onBack}
                      title={isUserView ? "Look up another bot" : "Back to bot list"}
                    >
                      ← {isUserView ? "Look up another bot" : "Back to list"}
                    </button>
                  )}
                  {!isUserView && botMeta.hasRefresh && (
                    <div className="reanalyze-wrapper" style={{ position: "relative" }}>
                    <button
                      ref={reAnalyzeBtnRef}
                      type="button"
                      className="btn"
                      onClick={() => setConfirmOpen((v) => !v)}
                      title="Re-scan the latest data from OKX and recalculate from scratch"
                    >
                      ⚡ Re-analyze
                    </button>

                    {confirmOpen && (
                      <>
                        {/* backdrop trong suốt để click ngoài đóng popup */}
                        <div
                          className="reanalyze-backdrop"
                          onClick={() => setConfirmOpen(false)}
                        />
                        <div className="reanalyze-confirm-popover" role="dialog" aria-modal="true">
                          <div className="reanalyze-confirm-icon">⚡</div>
                          <div className="reanalyze-confirm-title">Re-analyze this bot?</div>
                          <div className="reanalyze-confirm-body">
                            This will fetch live data from OKX and re-run all 10,000 Monte Carlo
                            simulations from scratch. The current snapshot will be overwritten.
                            This may take 30–60 seconds.
                          </div>
                          <div className="reanalyze-confirm-actions">
                            <button
                              type="button"
                              className="btn reanalyze-btn-confirm"
                              onClick={() => {
                                setConfirmOpen(false);
                                loadReport(true);
                              }}
                            >
                              ⚡ Confirm re-analyze
                            </button>
                            <button
                              type="button"
                              className="btn reanalyze-btn-cancel"
                              onClick={() => setConfirmOpen(false)}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  )}
                </div>
                <div className="report-head-divider" />
              </>
            )}
            <div className="report-title-group">
              <h1>{botMeta.name || code}</h1>
              {botMeta.name && botMeta.name !== code && (
                <span className="mono-code report-code-pill">{code}</span>
              )}
              {botMeta.marketTag && (
                <span className="venue-symbol-badge">{botMeta.marketTag}</span>
              )}
            </div>
          </div>

          {botMeta.snapshotTime ? (
            <div className="report-snapshot-notice">
              <span className="notice-icon">⏱️</span>
              <span>
                Analysis time: <strong>{botMeta.snapshotTime}</strong>
              </span>
            </div>
          ) : (
            <p>
              A 10-dimension quantitative risk profile, 10,000-scenario Monte Carlo simulation, and order book data live from OKX.
            </p>
          )}
        </div>
      )}

      {htmlContent.styles && (
        <style dangerouslySetInnerHTML={{ __html: htmlContent.styles }} />
      )}
      <div
        className="bot-report-inner-main"
        dangerouslySetInnerHTML={{ __html: htmlContent.bodyContent }}
      />
    </div>
  );
}
