"""Đo ĐỘ DỄ ĐỌC của văn bản tiếng Anh bằng Flesch Reading Ease và
Flesch-Kincaid grade level.

VÌ SAO MODULE NÀY TỒN TẠI: chủ dự án yêu cầu phần kết quả phân tích phải
"nhìn phát là hiểu được bản chất bot" -- cả người dùng lẫn quản trị đều đọc
nó. Cách làm dở là ghi vào prompt câu "hãy viết dễ hiểu" rồi tin rằng mô
hình nghe lời; không ai kiểm được, và nó lặp lại đúng thứ đã sai nhiều lần
trong module `narrative.py` kế bên: đặt ra một luật rồi không đo.

Chuyển sản phẩm sang tiếng Anh mở ra khả năng mà tiếng Việt không có: độ dễ
đọc trở thành ĐẠI LƯỢNG ĐO ĐƯỢC. Flesch (1948) và Flesch-Kincaid (Kincaid và
cộng sự, 1975) là hai công thức chuẩn công nghiệp, công bố học thuật, ai
cũng tra được -- cùng loại sở cứ mà `verdict.py` đòi hỏi cho mọi con số khác
trong sản phẩm này. Tiếng Việt KHÔNG có tương đương đáng tin (âm tiết và ranh
giới từ hoạt động khác hẳn), nên trước đây không thể đo.

    Flesch Reading Ease = 206.835 - 1.015 x (từ/câu) - 84.6 x (âm tiết/từ)
    Flesch-Kincaid grade = 0.39 x (từ/câu) + 11.8 x (âm tiết/từ) - 15.59

Hai công thức là CỐ ĐỊNH, không có gì để tinh chỉnh. Thứ duy nhất phải tự
cài -- và do đó là thứ duy nhất có thể sai -- là bộ đếm âm tiết. Nên nó được
kiểm riêng trên một danh sách từ có số âm tiết theo từ điển
(`Agent/none/test/test_readability.py`), trong đó cố ý gồm các từ tài chính mà
chính báo cáo này dùng liên tục (drawdown, leverage, volatility, portfolio,
ratio, position, simulation...). Đo được ở lần hiệu chỉnh cuối: 41/41.

KHÔNG dùng thư viện ngoài (textstat...): thêm một phụ thuộc chỉ để chạy hai
phép nhân là cái giá không đáng, và bộ đếm âm tiết của họ cũng là heuristic
y như ở đây, chỉ khác là ta không kiểm được nó trên từ vựng của mình.

ĐIỀU MODULE NÀY KHÔNG LÀM: nó không phán xét nội dung. Một đoạn văn sai bét
vẫn có thể dễ đọc. Độ dễ đọc là điều kiện CẦN, không phải điều kiện đủ --
tính đúng đắn do các cổng khác trong `narrative.py` lo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

__all__ = ["ReadabilityScore", "count_syllables", "measure_readability"]

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_SENTENCE_END_RE = re.compile(r"[.!?]+(?:\s|$)")
_VOWELS = "aeiouy"

# Nguyên âm đứng cạnh nhau nhưng thuộc HAI âm tiết khác nhau. Vòng đếm cụm
# nguyên âm bên dưới gộp chúng làm một, nên phải cộng bù.
#   i + nguyên âm : ra-ti-o, por-tfo-li-o, me-di-an, sce-na-ri-o, va-ri-ous
#   nguyên âm+ing : be-ing, do-ing, see-ing
_HIATUS_RE = (
    re.compile(r"i[aeouy]"),
    re.compile(r"[aeiou]ing\b"),
    re.compile(r"[aeiou]ism\b"),
)

# "-tion"/"-sion"/"-cion" là MỘT âm tiết ("shun"), khác hẳn "ra-ti-o" dù cùng
# khớp luật hiatus ở trên -- phải trừ lại, nếu không "po-si-tion" thành 4.
_SHUN_RE = re.compile(r"[tsc]ion")

# "ea" cuối từ SAU một âm tiết khác là hiatus (i-de-a, a-re-a); "ea" của
# "sea"/"tea" thì không, vì trước nó không có âm tiết nào.
_EA_HIATUS_RE = re.compile(r"[aeiou].*ea\b")


@dataclass(frozen=True)
class ReadabilityScore:
    """Kết quả đo. `flesch` cao = dễ đọc; `grade` là số năm đi học cần có."""

    words: int
    sentences: int
    syllables: int
    words_per_sentence: float
    syllables_per_word: float
    flesch: float
    grade: float


def count_syllables(word: str) -> int:
    """Số âm tiết của MỘT từ tiếng Anh, theo heuristic cụm nguyên âm.

    Luôn trả về ít nhất 1: mọi từ viết ra đều đọc được thành ít nhất một âm
    tiết, và trả 0 sẽ làm hỏng phép chia trung bình ở `measure_readability`.
    """
    text = word.lower().strip("'’-")
    if not text:
        return 0

    groups = 0
    previous_was_vowel = False
    for char in text:
        is_vowel = char in _VOWELS
        if is_vowel and not previous_was_vowel:
            groups += 1
        previous_was_vowel = is_vowel

    # "e" câm cuối từ: "make"/"code"/"ride" là 1 âm tiết. Giữ lại "-le"
    # ("ta-ble", "sim-ple"), "-ee" ("a-gree"), "-ye".
    if text.endswith("e") and not text.endswith(("le", "ee", "ye")) and groups > 1:
        groups -= 1

    # "-ed" chỉ thành âm tiết riêng sau t/d: "wan-ted" 2, "walked" 1.
    if text.endswith("ed") and groups > 1 and text[-3:-2] not in "td":
        groups -= 1

    for pattern in _HIATUS_RE:
        groups += len(pattern.findall(text))
    groups -= len(_SHUN_RE.findall(text))
    if _EA_HIATUS_RE.search(text):
        groups += 1

    return max(1, groups)


def measure_readability(text: str) -> Optional[ReadabilityScore]:
    """`None` khi không có từ nào đọc được -- nơi gọi phải coi đó là "không
    đo được", KHÔNG phải "điểm bằng 0" (một đoạn rỗng không hề dễ đọc).

    Đếm câu bằng dấu kết câu; tối thiểu là 1 để không bao giờ chia cho 0 với
    một đoạn văn không có dấu chấm nào.
    """
    words = _WORD_RE.findall(text or "")
    if not words:
        return None

    sentences = max(1, len([part for part in _SENTENCE_END_RE.split(text) if part.strip()]))
    syllables = sum(count_syllables(word) for word in words)

    words_per_sentence = len(words) / sentences
    syllables_per_word = syllables / len(words)

    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59

    return ReadabilityScore(
        words=len(words),
        sentences=sentences,
        syllables=syllables,
        words_per_sentence=round(words_per_sentence, 2),
        syllables_per_word=round(syllables_per_word, 3),
        flesch=round(flesch, 1),
        grade=round(grade, 1),
    )
