"""Chấm điểm bằng HẠNG PHÂN VỊ trong quần thể, thay cho ngưỡng tự đặt.

Yêu cầu gốc của chủ dự án: "nên có kiểm chứng và tính toán chính xác chứ
không phải dựa trên report rồi chọn bừa con số". Bộ test này khoá đúng hai
điều đó: điểm phải suy ra từ phân bố quan sát được, và khi quần thể không đủ
thì phải nói không đo được chứ không rơi về một thang bịa.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from Agent.backend.bot.analysis.population_reference import (
    MIN_POPULATION,
    clear_cache,
    PARAMETER_DIRECTION,
    percentile_rank,
    population_percentile,
    population_values,
)


@pytest.fixture(autouse=True)
def _fresh_cache() -> None:
    """Kho giả thay đổi trong cùng một tiến trình, nhanh hơn TTL 600s của
    cache rất nhiều -- không xoá thì phép đo thứ hai đọc lại số của phép đo
    thứ nhất."""
    clear_cache()


def _write_population(root: Path, parameter: str, values: List[float]) -> None:
    """Dựng một kho giả có đúng hình dạng `data/analysis/**/monte_carlo.json`."""
    for index, value in enumerate(values):
        folder = root / "report" / "single" / f"CODE{index}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "monte_carlo.json").write_text(
            json.dumps({"unique_code": f"CODE{index}", parameter: value}),
            encoding="utf-8",
        )


# --------------------------------------------------------------------------- #
# Hạng phân vị: định nghĩa và hai chiều ngữ nghĩa
# --------------------------------------------------------------------------- #


def test_percentile_is_the_share_of_the_population_that_is_better() -> None:
    population = [float(n) for n in range(10)]  # 0..9
    # 9 là giá trị lớn nhất -> với đại lượng "cao = xấu", nó phải gần 100.
    assert percentile_rank(9.0, population, higher_is_worse=True) == 95.0
    assert percentile_rank(0.0, population, higher_is_worse=True) == 5.0
    # Cùng dữ liệu, đại lượng "cao = tốt" thì đảo chiều.
    assert percentile_rank(9.0, population, higher_is_worse=False) == pytest.approx(5.0)


def test_ties_share_a_midrank_instead_of_the_first_taking_everything() -> None:
    population = [5.0] * MIN_POPULATION
    # Toàn bộ quần thể bằng nhau -> đúng giữa thang, không phải 0 hay 100.
    assert percentile_rank(5.0, population, higher_is_worse=True) == 50.0


def test_a_value_outside_the_observed_range_is_clamped_not_extrapolated() -> None:
    population = [float(n) for n in range(MIN_POPULATION)]
    assert percentile_rank(1_000.0, population, higher_is_worse=True) == 100.0
    assert percentile_rank(-1_000.0, population, higher_is_worse=True) == 0.0


# --------------------------------------------------------------------------- #
# Quần thể quá nhỏ -> KHÔNG chấm, không bịa thang thay thế
# --------------------------------------------------------------------------- #


def test_population_below_the_minimum_returns_no_score() -> None:
    population = [1.0, 2.0, 3.0]
    assert percentile_rank(2.0, population, higher_is_worse=True) is None


def test_population_percentile_needs_enough_bots(tmp_path: Path) -> None:
    _write_population(tmp_path, "mc_p_ruin", [1.0, 2.0, 3.0])
    assert population_percentile(tmp_path, "mc_p_ruin", 2.0) is None

    _write_population(tmp_path, "mc_p_ruin", [float(n) for n in range(MIN_POPULATION)])
    clear_cache()
    scored = population_percentile(tmp_path, "mc_p_ruin", 5.0)
    assert scored is not None
    assert scored["population_size"] >= MIN_POPULATION


# --------------------------------------------------------------------------- #
# Không đoán hướng, không đọc rác
# --------------------------------------------------------------------------- #


def test_unknown_parameter_is_not_guessed(tmp_path: Path) -> None:
    _write_population(tmp_path, "mc_p_ruin", [float(n) for n in range(MIN_POPULATION)])
    assert population_percentile(tmp_path, "tham_so_la", 1.0) is None


def test_every_declared_parameter_has_an_explicit_direction() -> None:
    assert PARAMETER_DIRECTION, "phải khai báo hướng ngữ nghĩa cho từng tham số"
    assert all(isinstance(v, bool) for v in PARAMETER_DIRECTION.values())
    # Lợi nhuận cao hơn KHÔNG được coi là rủi ro cao hơn.
    assert PARAMETER_DIRECTION["mc_profit_p50_pct"] is False
    assert PARAMETER_DIRECTION["mc_p_ruin"] is True


def test_corrupt_and_non_numeric_entries_are_skipped(tmp_path: Path) -> None:
    _write_population(tmp_path, "mc_p_ruin", [1.0, 2.0, 3.0])
    bad = tmp_path / "report" / "single" / "X"
    bad.mkdir(parents=True, exist_ok=True)
    (bad / "monte_carlo.json").write_text("{khong phai json", encoding="utf-8")
    text = tmp_path / "report" / "single" / "Y"
    text.mkdir(parents=True, exist_ok=True)
    (text / "monte_carlo.json").write_text(
        json.dumps({"mc_p_ruin": "khong phai so"}), encoding="utf-8"
    )
    assert population_values(tmp_path, "mc_p_ruin") == [1.0, 2.0, 3.0]


def test_booleans_are_not_counted_as_numbers(tmp_path: Path) -> None:
    folder = tmp_path / "report" / "single" / "Z"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "monte_carlo.json").write_text(
        json.dumps({"mc_p_ruin": True}), encoding="utf-8"
    )
    assert population_values(tmp_path, "mc_p_ruin") == []


# --------------------------------------------------------------------------- #
# Trên KHO THẬT: điểm phải giải thích được bằng chính dữ liệu
# --------------------------------------------------------------------------- #


def test_real_store_scores_are_explainable_from_the_real_distribution() -> None:
    from Agent.backend.infra.config import config

    data_dir = Path(config.BASE_DIR) / "data"
    values = population_values(data_dir, "mc_p_ruin")
    if len(values) < MIN_POPULATION:
        return  # kho chưa đủ bot -- không phải lỗi của module này

    worst = max(values)
    best = min(values)
    scored_worst = population_percentile(data_dir, "mc_p_ruin", worst)
    scored_best = population_percentile(data_dir, "mc_p_ruin", best)
    assert scored_worst is not None and scored_best is not None
    # Bot tệ nhất quần thể phải có điểm cao hơn bot tốt nhất, và mọi con số
    # kèm theo phải là số thật của quần thể chứ không phải hằng số.
    assert scored_worst["score"] > scored_best["score"]
    assert scored_worst["population_size"] == len(values)
    assert scored_worst["population_min"] == best
    assert scored_worst["population_max"] == worst
