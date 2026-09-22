"""Kiểm thử `Agent/backend/qc/reporting/readability.py`.

Trọng tâm: hai công thức Flesch là CỐ ĐỊNH và chuẩn công bố, không có gì để
kiểm ngoài việc chép đúng. Thứ duy nhất tự cài -- và do đó là thứ duy nhất
có thể sai -- là BỘ ĐẾM ÂM TIẾT. Nên phần lớn file này kiểm đúng cái đó,
trên những từ có số âm tiết không thể tranh cãi, và cố ý gồm từ vựng tài
chính mà chính báo cáo dùng liên tục.
"""

from __future__ import annotations

from Agent.backend.report.qc.reporting.readability import (
    count_syllables,
    measure_readability,
)

# Số âm tiết theo từ điển. Nhóm theo ĐẶC ĐIỂM NGỮ ÂM đang được kiểm, để khi
# một dòng đỏ thì biết ngay luật nào vỡ chứ không phải dò cả bảng.
_SILENT_E = {"make": 1, "time": 1, "code": 1, "ride": 1, "close": 1}
_LE_ENDING = {"table": 2, "simple": 2, "little": 2, "cycle": 2}
_DOUBLE_E = {"agree": 2, "free": 1, "see": 1}
_ED_ENDING = {"walked": 1, "closed": 1, "wanted": 2, "needed": 2, "traded": 2}
# Hiatus: hai nguyên âm kề nhau nhưng khác âm tiết -- luật khó nhất.
_HIATUS = {
    "ratio": 3,
    "median": 3,
    "portfolio": 4,
    "scenario": 4,
    "various": 3,
    "serious": 3,
    "period": 3,
    "bias": 2,
    "idea": 3,
    "area": 3,
    "being": 2,
    "doing": 2,
}
# "-tion" là MỘT âm tiết, dù khớp cùng luật hiatus ở trên.
_SHUN = {"position": 3, "simulation": 4, "correlation": 4, "decision": 3, "session": 2}
# Không phải hiatus, dễ bị cộng dư.
_NOT_HIATUS = {"sea": 1, "tea": 1, "ration": 2}
# Từ vựng tài chính của chính sản phẩm này.
_DOMAIN = {
    "risk": 1,
    "profit": 2,
    "drawdown": 2,
    "leverage": 3,
    "exposure": 3,
    "volatility": 5,
    "probability": 5,
    "quality": 3,
    "evidence": 3,
    "confidence": 3,
    "account": 2,
    "capital": 3,
    "trading": 2,
}

_ALL = {
    **_SILENT_E,
    **_LE_ENDING,
    **_DOUBLE_E,
    **_ED_ENDING,
    **_HIATUS,
    **_SHUN,
    **_NOT_HIATUS,
    **_DOMAIN,
}


def test_syllable_counter_matches_the_dictionary() -> None:
    wrong = {w: (count_syllables(w), n) for w, n in _ALL.items() if count_syllables(w) != n}
    assert not wrong, f"đếm sai (từ: (đếm được, đúng)): {wrong}"


def test_every_written_word_has_at_least_one_syllable() -> None:
    """Trả 0 sẽ làm hỏng phép chia trung bình ở `measure_readability`."""
    for word in ("a", "I", "the", "rhythm", "x", "'"):
        assert count_syllables(word) >= 1 or word == "'"
    assert count_syllables("") == 0


# --------------------------------------------------------------------------- #
# Phép đo tổng hợp
# --------------------------------------------------------------------------- #


def test_returns_none_for_text_with_no_words() -> None:
    """"Không đo được" KHÁC "điểm 0": một đoạn rỗng không hề dễ đọc."""
    for empty in ("", "   ", "123 456", "!!!"):
        assert measure_readability(empty) is None


def test_simpler_prose_always_scores_easier_than_denser_prose() -> None:
    """Bất biến CHIỀU -- thứ duy nhất đáng khoá ở đây.

    Khoá một con số tuyệt đối ("đoạn này phải đạt 52,3") là tự trói vào một
    mẫu văn cụ thể; điều thực sự cần đúng là thước đo xếp hạng đúng chiều.
    """
    simple = "The bot makes small gains. It also takes small losses. The risk is low."
    dense = (
        "The heterogeneity of intertemporal substitution elasticities across "
        "demographic cohorts necessitates reconsideration of representative-agent "
        "formulations under pronounced non-linearities."
    )
    easy = measure_readability(simple)
    hard = measure_readability(dense)
    assert easy is not None and hard is not None
    assert easy.flesch > hard.flesch
    assert easy.grade < hard.grade


def test_longer_sentences_alone_make_text_harder() -> None:
    """Giữ nguyên từ vựng, chỉ nối câu lại -- điểm phải tụt."""
    short = "Risk is low. Quality is good. The sample is small."
    joined = "Risk is low and quality is good and the sample is small."
    a = measure_readability(short)
    b = measure_readability(joined)
    assert a is not None and b is not None
    assert a.flesch > b.flesch


def test_counts_are_self_consistent() -> None:
    score = measure_readability("The bot holds losing trades. It rarely cuts them.")
    assert score is not None
    assert score.words == 9
    assert score.sentences == 2
    assert score.syllables >= score.words  # mỗi từ tối thiểu một âm tiết
    assert abs(score.words_per_sentence - score.words / score.sentences) < 0.01
    assert abs(score.syllables_per_word - score.syllables / score.words) < 0.01


def test_text_without_terminal_punctuation_is_one_sentence_not_zero() -> None:
    score = measure_readability("a bot with no full stop anywhere in the text")
    assert score is not None
    assert score.sentences == 1
