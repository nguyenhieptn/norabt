"""Kiểm nghiệm thu ĐẦU-CUỐI: hệ thống có THẬT SỰ chạy đúng không.

VÌ SAO CẦN, dù đã có 1.576 test: bộ test kiểm từng mảnh với dữ liệu giả.
Nó không trả lời được câu "chạy thật thì sao". Ngày 19/09 khoảng cách đó
cắn thật: toàn bộ test xanh, nhưng lượt chấm 30 bot thật cho ra 18/30 câu
dự phòng thay vì văn thật -- và dòng log lại ghi "narrative OK" cho cả 30,
vì nó chỉ báo "lượt gọi kết thúc" chứ không báo "sinh được văn". Báo cáo
dựa trên dòng log đó sai tới mức đảo ngược kết luận.

NGUYÊN TẮC CỦA FILE NÀY: chỉ kiểm HIỆN VẬT THẬT -- file trên đĩa, phản hồi
HTTP thật, HTML thật. Không đọc log, không tin thông điệp tiến độ, không
suy từ việc "hàm chạy xong không ném lỗi".

Chạy:  python3 -m Agent.none.scripts.acceptance_check
Mã thoát 0 khi mọi mục ĐẠT, 1 khi có mục TRƯỢT.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

REPO = Path(__file__).resolve().parents[3]
# 2026-09: assessment_store.persist ghi vào data/report/<bot_id>/latest.json
# (không còn data/assessment/<venue>/<asset>/bot/.../assessment.json)
REPORT_DIR = REPO / "Agent" / "data" / "report"
BASE_URL = "http://127.0.0.1:8770"

# Dấu phụ CHỈ có trong tiếng Việt. Cố ý KHÔNG gồm "ó"/"é" trần: chúng xuất
# hiện trong tên riêng nước ngoài hợp lệ (López de Prado) và trong tiếng
# Trung/Nhật của chính nick name người dùng OKX tự đặt.
_VIETNAMESE = re.compile(
    r"[ăâđêôơưàảãạằẳẵặầẩẫậèẻẽẹềểễệìỉĩịòỏõọồổỗộờởỡợùủũụừửữựỳỷỹỵ]", re.IGNORECASE
)

# Tên hiển thị do chủ tài khoản OKX tự đặt -- có thể là bất cứ thứ tiếng gì
# và KHÔNG phải lỗi dịch. Bỏ qua mọi đường dẫn đi qua các khoá này.
_USER_TEXT_KEYS = {"nick_name", "name", "display_name", "untrusted_nick_name"}


def _walk(node: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _USER_TEXT_KEYS:
                continue
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")
    elif isinstance(node, str) and _VIETNAMESE.search(node):
        yield path, node


class Report:
    def __init__(self) -> None:
        self.rows: List[Tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> None:
        self.rows.append((ok, name, detail))

    def render(self) -> bool:
        width = max(len(name) for _, name, _ in self.rows)
        for ok, name, detail in self.rows:
            mark = "ĐẠT   " if ok else "TRƯỢT "
            print(f"  {mark} {name.ljust(width)}  {detail}")
        failed = [name for ok, name, _ in self.rows if not ok]
        print()
        if failed:
            print(f"TRƯỢT {len(failed)}/{len(self.rows)}: {', '.join(failed)}")
            return False
        print(f"ĐẠT toàn bộ {len(self.rows)} mục")
        return True


def check_stored_assessments(report: Report) -> None:
    """Kho dữ liệu: schema, khoá, và VĂN THẬT chứ không phải câu dự phòng.

    2026-09: persist ghi vào data/report/<bot_id>/latest.json thay vì
    data/assessment/<venue>/<asset>/bot/.../assessment.json.
    """
    from Agent.backend.llm.narrative import FALLBACK_NARRATIVE_VI
    from Agent.backend.report.qc.reporting.readability import measure_readability

    files = sorted(REPORT_DIR.glob("*/latest.json"))
    report.check(bool(files), "kho có dữ liệu", f"{len(files)} file")
    if not files:
        return

    fallback_text = FALLBACK_NARRATIVE_VI.strip()
    wrong_schema, vietnamese, empty, fallback, grades = [], [], [], [], []

    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        name = doc.get("bot", {}).get("nick_name", path.parent.name)

        if doc.get("schema_version") != "bot_assessment.v3":
            wrong_schema.append(name)
        for field_path, _value in _walk(doc):
            vietnamese.append(f"{name}{field_path}")

        text = (doc.get("expert_assessment") or "").strip()
        if not text:
            empty.append(name)
        elif text == fallback_text:
            fallback.append(name)
        else:
            score = measure_readability(text)
            if score is not None:
                grades.append(score.grade)

    report.check(not wrong_schema, "schema v3 ở mọi file", f"{len(wrong_schema)} sai")
    report.check(
        not vietnamese,
        "không còn tiếng Việt trong JSON",
        f"{len(vietnamese)} trường" + (f" — ví dụ {vietnamese[0]}" if vietnamese else ""),
    )
    # Bot giấu sổ lệnh hợp lệ khi không có văn; ngưỡng dưới đây chỉ chặn
    # trường hợp CẢ KHO rỗng, không bắt từng ca lẻ.
    report.check(
        len(empty) <= 1, "expert_assessment có mặt", f"{len(empty)}/{len(files)} rỗng"
    )
    report.check(
        not fallback,
        "văn thật, không phải câu dự phòng",
        f"{len(fallback)}/{len(files)} rơi về dự phòng"
        + (f" — {', '.join(fallback[:4])}" if fallback else ""),
    )
    if grades:
        grades.sort()
        worst = grades[-1]
        report.check(
            worst <= 16.0,
            "độ dễ đọc trong tầm",
            f"grade {grades[0]:.1f}..{worst:.1f} (trần 16)",
        )



def check_report_folders_consistent(report: Report) -> None:
    """Mỗi bot hoàn chỉnh trong data/report/ có đủ 3 file: latest.json,
    monte_carlo.json, performance.json.

    2026-09: schema mới không còn index.json -- bộ ba file trên đủ để
    MCP (`list_assessed_bots`, `get_assessment`) đọc trực tiếp từ đĩa.
    Kiểm này thay thế check_index_matches_disk cũ.

    Thư mục không phải bot (không có latest.json) bị bỏ qua hoàn toàn.
    Bot chỉ có latest.json (đang phân tích hoặc thiếu dữ liệu monte carlo)
    được tính là cảnh báo, không hard-fail.
    """
    CORE = "latest.json"
    FULL = {"latest.json", "monte_carlo.json", "performance.json"}
    # Chỉ xét thư mục có latest.json -- bỏ qua state/, users/ và các thư mục phụ.
    bot_dirs = sorted(
        d for d in REPORT_DIR.iterdir()
        if d.is_dir() and (d / CORE).exists()
    )
    missing: List[str] = []
    for d in bot_dirs:
        have = {f.name for f in d.iterdir() if f.is_file()}
        if not FULL.issubset(have):
            missing.append(f"{d.name}: thiếu {FULL - have}")
    # Cảnh báo nhưng không fail nếu < 20% bot chưa đủ bộ ba file
    # (thường xảy ra khi một lượt phân tích đang chạy dở).
    ratio_ok = len(missing) / max(len(bot_dirs), 1) < 0.20
    report.check(
        ratio_ok,
        "mỗi thư mục report có đủ 3 file",
        f"{len(bot_dirs)} bot đầy đủ latest.json, {len(missing)} thiếu monte_carlo/performance"
        + (f" — ví dụ {missing[0]}" if missing else ""),
    )


# Khoá mà `report_page.py` đọc từ khối `simulation` để VẼ, nhưng không tầng
# nào giữa mô phỏng và đĩa từng chuyển tiếp -- mỗi khoá thiếu là một ô trống
# hoặc một vạch "—" trên trang, im lặng. Danh sách này cố ý liệt kê tay chứ
# không grep: nó là HỢP ĐỒNG, và một khoá bị xoá khỏi report_page phải là
# một sửa đổi có chủ ý ở cả hai nơi.
_SIMULATION_CONTRACT = (
    "profit_pct_p25",
    "profit_pct_p75",
    "median_max_drawdown",
    "p90_max_drawdown",
    "p99_max_drawdown",
    "p_5_loss_streak_baseline",
    "p_5_loss_streak_excess",
    "p_10_loss_streak",
    "sample_is_thin",
    "observed_span_days",
    "horizon_exceeds_observed",
)

# Cùng lý do, cho khối `scoring`: trọng số/độ tin cậy từng chiều và lý do
# một chiều không đo được.
_SCORING_CONTRACT = ("dimension_weights", "dimension_confidence", "total_weight")

# Khoá của khối `evidence` mà trang đọc để giải thích ĐỘ TIN CẬY. Thiếu
# chúng thì trang phải nói "bản ghi đã lưu không mang chi tiết này" -- đúng
# trạng thái suy giảm mà đợt hội tụ hai-hình-dạng đã dẹp.
_EVIDENCE_CONTRACT = ("data_quality", "market_available")


def check_persisted_contract(report: Report) -> None:
    """Các khoá trang báo cáo ĐỌC ĐỂ VẼ phải thật sự có trên đĩa."""
    files = sorted(REPORT_DIR.glob("*/latest.json"))
    if not files:
        return
    missing_sim: List[str] = []
    missing_score: List[str] = []
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        sim = doc.get("simulation") or {}
        scoring = doc.get("scoring") or {}
        missing_sim += [k for k in _SIMULATION_CONTRACT if k not in sim]
        missing_score += [k for k in _SCORING_CONTRACT if k not in scoring]
    report.check(
        not missing_sim,
        "khoá mô phỏng trang báo cáo vẽ",
        f"{len(missing_sim)} thiếu"
        + (f" — ví dụ {sorted(set(missing_sim))[:3]}" if missing_sim else ""),
    )
    missing_ev: List[str] = []
    ranks: List[Any] = []
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        ev = doc.get("evidence") or {}
        missing_ev += [k for k in _EVIDENCE_CONTRACT if k not in ev]
        ranks.append((doc.get("bot") or {}).get("rank_in_cohort"))
    report.check(
        not missing_ev,
        "khoá bằng chứng hai-hình-dạng",
        f"{len(missing_ev)} thiếu"
        + (f" — ví dụ {sorted(set(missing_ev))[:2]}" if missing_ev else ""),
    )
    # Thứ hạng là thuộc tính của cả quần thể: mỗi bot một số, không trùng.
    # Chạy lại lẻ từng bịa ra hạng 1 rồi đè lên bot đứng nhất thật.
    real_ranks = [r for r in ranks if isinstance(r, int)]
    report.check(
        len(set(real_ranks)) == len(files) == len(real_ranks),
        "thứ hạng duy nhất trên cả đàn",
        f"{len(set(real_ranks))} hạng khác nhau / {len(files)} bot",
    )
    report.check(
        not missing_score,
        "khoá chấm điểm trang báo cáo vẽ",
        f"{len(missing_score)} thiếu"
        + (f" — ví dụ {sorted(set(missing_score))[:3]}" if missing_score else ""),
    )


def _get_json(path: str, payload: Dict[str, Any] | None = None) -> Any:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def check_live_service(report: Report) -> None:
    """Dịch vụ đang chạy: phản hồi HTTP THẬT, không phải hàm gọi trực tiếp."""
    try:
        health = _get_json("/healthz")
    except (urllib.error.URLError, OSError) as exc:
        report.check(False, "dịch vụ đang chạy", f"không gọi được: {exc}")
        return
    report.check(True, "dịch vụ đang chạy", f"narrative={health.get('narrative')}")

    rows = _get_json("/api/bots")
    items = rows.get("bots", rows) if isinstance(rows, dict) else rows
    scored = [r for r in items if r.get("risk") is not None]
    report.check(
        len(scored) >= max(1, len(items) - 1),
        "/api/bots trả điểm thật",
        f"{len(scored)}/{len(items)} hàng có điểm rủi ro",
    )
    leaks = [p for r in items for p, _ in _walk(r)]
    report.check(not leaks, "/api/bots không có tiếng Việt", f"{len(leaks)} trường")

    if not scored:
        return
    code = scored[0].get("code")
    result = _get_json("/api/analyze", {"code": code})
    leaks = [f"{p}" for p, _ in _walk(result)]
    report.check(
        not leaks,
        "/api/analyze không có tiếng Việt",
        f"{len(leaks)} trường" + (f" — ví dụ {leaks[0]}" if leaks else ""),
    )
    report.check(
        result.get("risk") is not None and result.get("verdict"),
        "/api/analyze trả kết luận",
        f"verdict={result.get('verdict')!r} risk={result.get('risk')}",
    )

    with urllib.request.urlopen(f"{BASE_URL}/bot/{code}", timeout=120) as response:
        html = response.read().decode("utf-8")
    # Bỏ chú thích CSS/JS: chúng không hiện ra cho người đọc.
    visible = re.sub(r"/\*.*?\*/", " ", html, flags=re.DOTALL)
    visible = re.sub(r"<style.*?</style>|<script.*?</script>", " ", visible, flags=re.DOTALL)
    found = _VIETNAMESE.findall(visible)
    report.check(
        not found,
        "trang /bot/<code> không có tiếng Việt",
        f"{len(found)} ký tự có dấu",
    )


def main() -> int:
    print("KIỂM NGHIỆM THU ĐẦU-CUỐI — chỉ kiểm hiện vật thật\n")
    report = Report()
    check_stored_assessments(report)
    check_report_folders_consistent(report)
    check_persisted_contract(report)
    check_live_service(report)
    print()
    return 0 if report.render() else 1


if __name__ == "__main__":
    sys.exit(main())
