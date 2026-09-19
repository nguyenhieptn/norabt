"""Chọn và giải NHIỀU thị trường một bot thực sự giao dịch, theo MỤC TIÊU
PHỦ SÓNG (tỉ trọng exposure cộng dồn), thay vì luôn đúng cố định 1 hoặc 2
thị trường như trước (thị trường CHÍNH + PHỤ).

Bối cảnh (đo thật trên 30 bot, project owner, 2026-09-17): mỗi bot chạm
trung vị 13 mã (cao nhất 69), nhưng thị trường được chấm trước đây (chỉ
CHÍNH + PHỤ) chỉ phủ trung vị 44.1% giá trị giao dịch -- 23/30 bot dưới
60%. Đo theo SỐ THỊ TRƯỜNG giải được: 1 mã -> 44.1% coverage (3/30 đạt
>=80%) · 2 mã -> 61.7% (9/30) · 3 mã -> 75.3% (10/30). Nhưng để phủ 80%,
trung vị chỉ cần 4 mã (phân vị 75 là 7, nhiều nhất 20) -- tức số mã cần
giải PHỤ THUỘC VÀO TỪNG BOT, không phải một hằng số đếm cứng nhỏ. Module
này thay "luôn giải đúng N mã" bằng "giải tới khi đạt X% phủ sóng, có trần
cứng để không bot nào (có bot chạm 69 mã) kéo sập ngân sách một lượt
phân tích".

`plan_market_coverage()` là phần THUẦN (không I/O): chọn ra bộ symbol cần
thử giải, dựa trên `symbol_exposure_share` bot tự báo cáo (xem
Agent/backend/mcp/service.py::_resolve_identity_market -- tỉ trọng theo
giá trị danh nghĩa/notional các lệnh đã chốt, fallback đếm lệnh rồi fallback
vị thế đang mở). `resolve_planned_markets()` là phần THỰC SỰ gọi mạng (qua
một `resolve_fn` callback do caller cung cấp -- caller chịu trách nhiệm cho
nó luôn đi qua MarketService/AdaptiveThrottle của
Agent/backend/sources/market_source.py, module này không tự gọi OKX),
song song hoá với cùng kỷ luật "thị trường CHÍNH đợi tới khi xong, các thị
trường còn lại chia nhau MỘT ngân sách chờ chung" mà bản trước của
pipeline.py/cohort.py (giải đúng 1 thị trường phụ) đã áp dụng -- ở đây chỉ
tổng quát hoá từ đúng 1 thị trường phụ thành N thị trường phụ.

Dùng chung bởi cả `pipeline.py::RiskSupervisionPipeline.run` (một bot mỗi
lượt `/api/analyze`) và `qc/reporting/cohort.py::CohortAssessmentService.scan`
(hàng chục bot một lượt, với cache `markets` riêng của nó để khỏi giải lại
cùng một symbol hai lần trong cùng một lượt scan) để không lặp lại logic
phân luồng ở hai nơi.

RÀNG BUỘC CỨNG của nhiệm vụ này (không đổi trong đợt này): mọi thị trường
NGOÀI thị trường CHÍNH chỉ để TRÌNH BÀY/đo độ phủ, không bao giờ được
truyền vào `QCCoreService.assess_bot()` -- hàm đó vẫn chỉ nhận đúng MỘT
`market`. Việc gộp nhiều thị trường vào công thức chấm điểm là một thay đổi
lớn về ngữ nghĩa, để riêng một đợt khác có đối chiếu trước/sau đàng hoàng.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Kiểu MarketResult thật (Agent/backend/market/schemas/market_result.py)
# không được import trực tiếp ở đây: module này không cần biết hình dạng
# của nó, chỉ chuyển tiếp nguyên vẹn những gì `resolve_fn` (do caller cung
# cấp) trả về -- tránh một phụ thuộc không cần thiết. `Any` thay vì một
# TypeVar: một alias generic không tự parameterize được gọn ở chữ ký hàm
# bên dưới, và caller (pipeline.py/cohort.py) đã tự đánh kiểu cụ thể ở phía
# của họ khi bọc kết quả vào ResolvedMarketShare/CoveredMarketRow.
ResolveFn = Callable[[str], Tuple[Optional[Any], str]]

# --------------------------------------------------------------------------- #
# Mục tiêu phủ sóng -- 0.80 (không phải 1.0): đo thật cho thấy phân vị 75 chỉ
# cần 7 mã để đạt 80%, trong khi phần đuôi dài (bot chạm tới 69 mã) sẽ không
# bao giờ phủ 100% với chi phí hợp lý -- 80% là mức "đại diện được cho phần
# lớn hoạt động thật" mà không bắt MỌI bot trả giá bằng việc giải hàng chục
# thị trường.
MARKET_COVERAGE_TARGET = 0.80
MARKET_COVERAGE_TARGET_PCT = MARKET_COVERAGE_TARGET * 100.0

# Trần cứng số thị trường một bot được phép kéo vào MỘT lượt phân tích -- có
# bot chạm tới 69 mã (Ail.Wang), để nó tự do kéo theo đúng mục tiêu phủ sóng
# sẽ xé nát ngân sách CPU/mạng của một lượt chạy. Phân vị 75 chỉ cần 7 mã để
# đạt 80%; 8 chừa dư đúng một mã so với đó.
MAX_MARKETS_PER_BOT = 8

# Số luồng song song tối đa khi giải nhiều thị trường cho MỘT bot -- trần ở
# 6 vì máy chỉ được cấp <=12 core/<=14GB cho toàn dự án (ResourceGuard) và
# đang chạy 15 site production khác trên cùng máy.
MAX_MARKET_RESOLVE_WORKERS = 6

# Mọi thị trường NGOÀI thị trường CHÍNH chỉ để trình bày/đo độ phủ, không
# bao giờ vào công thức chấm điểm -- xem QCCoreService.assess_bot() (chỉ
# nhận đúng 1 market). Vì vậy chúng chia nhau MỘT ngân sách chờ CHUNG, tách
# khỏi thị trường CHÍNH: đo thật (project owner, 2026-09-17) giải một thị
# trường mất ~6.2-6.6s bình thường -- 15s là gấp hơn 2 lần mức đó, đủ dư cho
# một lần chậm bất thường. Vì đây là một ngân sách CHUNG (một lần
# `concurrent.futures.wait` cho MỌI thị trường phụ, không phải 15s nhân
# theo số lượng), thời gian tối đa bị kéo dài thêm vẫn bị chặn ở đúng
# 15s dù kế hoạch có bao nhiêu thị trường phụ.
ADDITIONAL_MARKET_TIMEOUT_SECONDS = 15.0


def plan_market_coverage(
    primary_symbol: str,
    exposure_share: Mapping[str, float],
    *,
    target: float = MARKET_COVERAGE_TARGET,
    max_markets: int = MAX_MARKETS_PER_BOT,
) -> List[str]:
    """Chọn danh sách symbol CẦN THỬ GIẢI cho một bot.

    Thị trường CHÍNH (`primary_symbol`) luôn đứng đầu và luôn có mặt --
    ngay cả khi bot không đo được exposure nào (ví dụ `exposure_share`
    rỗng), thị trường nó ĐANG giao dịch luôn phải được thử giải để chấm
    điểm. Các mã còn lại thêm dần theo `exposure_share` giảm dần, dừng khi
    tỉ trọng CỘNG DỒN (kể cả thị trường CHÍNH) đạt `target`, hoặc đã chạm
    `max_markets`.

    Đây là kế hoạch DỰA TRÊN SỐ EXPOSURE BOT TỰ BÁO CÁO, không phải độ phủ
    THỰC ĐẠT ĐƯỢC -- một mã trong danh sách này có thể không có dữ liệu thị
    trường công khai (cổ phiếu như SNDK, MU, SKHYNIX, LITE, PUMP, HYPE,
    CRCL...); `resolve_planned_markets` bên dưới xử lý phần đó, module này
    không suy diễn/thay thế gì cả.
    """
    primary_share = float(exposure_share.get(primary_symbol, 0.0) or 0.0)
    planned = [primary_symbol]
    cumulative = primary_share
    if cumulative < target:
        candidates = sorted(
            (name for name in exposure_share if name != primary_symbol),
            key=lambda name: exposure_share[name],
            reverse=True,
        )
        for name in candidates:
            if len(planned) >= max_markets:
                break
            planned.append(name)
            cumulative += float(exposure_share.get(name, 0.0) or 0.0)
            if cumulative >= target:
                break
    return planned


def resolve_planned_markets(
    planned_symbols: Sequence[str],
    primary_symbol: str,
    resolve_fn: ResolveFn,
    *,
    timeout_seconds: float = ADDITIONAL_MARKET_TIMEOUT_SECONDS,
    max_workers: int = MAX_MARKET_RESOLVE_WORKERS,
    thread_name_prefix: str = "norabt-market-resolve",
) -> Dict[str, Tuple[Optional[Any], str]]:
    """Giải song song từng symbol trong `planned_symbols` qua `resolve_fn`
    (do caller cung cấp -- xem docstring module cho lý do nó phải luôn đi
    qua MarketService/AdaptiveThrottle). Trả
    `{symbol: (market_hoặc_None, resolution_hoặc_lý_do)}` -- CHỈ chứa
    symbol đã thật sự có kết quả trong ngân sách chờ; một symbol timeout
    đơn giản KHÔNG có mặt trong dict trả về (caller tự suy ra "hết hạn
    chờ" từ việc symbol đó vắng mặt, xem pipeline.py/cohort.py).

    `primary_symbol` được CHỜ TỚI KHI XONG, không hạn chờ -- thị trường
    chính chậm thì đành chờ, không có gì thay thế được nó để chấm điểm.
    Mọi symbol khác trong `planned_symbols` chia sẻ MỘT ngân sách chờ DUY
    NHẤT `timeout_seconds` (không nhân theo số lượng) -- xem hằng số
    `ADDITIONAL_MARKET_TIMEOUT_SECONDS`.

    `pool.shutdown(wait=False)` ở `finally`, KHÔNG dùng `with` block: một
    future phụ vừa hết hạn chờ có thể vẫn đang chạy trong nền -- không chờ
    nó nữa (đó chính là lý do timeout tồn tại), để nó tự kết thúc, không rò
    tài nguyên.
    """
    if not planned_symbols:
        return {}
    if len(planned_symbols) == 1:
        # Đúng một symbol (thường là bot chỉ giao dịch một mã) -- không cần
        # threadpool cho một future duy nhất.
        return {planned_symbols[0]: resolve_fn(planned_symbols[0])}

    workers = max(1, min(len(planned_symbols), max_workers))
    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=workers, thread_name_prefix=thread_name_prefix
    )
    results: Dict[str, Tuple[Optional[Any], str]] = {}
    try:
        futures = {
            symbol: pool.submit(resolve_fn, symbol) for symbol in planned_symbols
        }
        primary_future = futures.get(primary_symbol)
        if primary_future is not None:
            results[primary_symbol] = primary_future.result()

        other_futures = {
            symbol: future
            for symbol, future in futures.items()
            if symbol != primary_symbol
        }
        if other_futures:
            done, _not_done = concurrent.futures.wait(
                list(other_futures.values()), timeout=timeout_seconds
            )
            for symbol, future in other_futures.items():
                if future not in done:
                    logger.info(
                        "norabt market coverage: quá %.0fs chờ thị trường phụ "
                        "(%s) -- bỏ qua, ghi nhận CHƯA ĐO ĐƯỢC, không kéo cả "
                        "lượt phân tích",
                        timeout_seconds,
                        symbol,
                    )
                    continue
                try:
                    results[symbol] = future.result()
                except Exception:  # noqa: BLE001 - thị trường phụ chỉ để
                    # trình bày/đo độ phủ, một lỗi bất ngờ ở đây không được
                    # phép làm hỏng cả lượt phân tích chính.
                    logger.exception(
                        "norabt market coverage: lỗi khi giải thị trường phụ "
                        "(%s) -- bỏ qua",
                        symbol,
                    )
    finally:
        pool.shutdown(wait=False)
    return results
