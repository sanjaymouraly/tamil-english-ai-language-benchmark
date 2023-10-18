"""Unit tests for aggregation and bootstrap confidence intervals."""

from app.evaluation.aggregation import group_stats, paired_difference


def test_group_stats_basic():
    stats = group_stats([0.5, 0.6, 0.7, 0.8, 0.9, 0.5, 0.6, 0.7])
    assert stats.count == 8
    assert abs(stats.mean - 0.6625) < 0.01


def test_group_stats_empty():
    stats = group_stats([])
    assert stats.mean is None


def test_group_stats_with_none():
    stats = group_stats([0.5, None, 0.7])
    assert stats.count == 2
    assert abs(stats.mean - 0.6) < 0.01


def test_bootstrap_ci_present_for_large_sample():
    values = [i / 100 for i in range(50)]
    stats = group_stats(values)
    assert stats.ci_low is not None
    assert stats.ci_high is not None
    assert stats.ci_low <= stats.mean <= stats.ci_high


def test_bootstrap_ci_absent_for_small_sample():
    stats = group_stats([0.5, 0.6, 0.7])
    assert stats.ci_low is None  # too few samples


def test_paired_difference():
    a = [0.9, 0.8, 0.7, 0.9, 0.8, 0.7, 0.9, 0.8]
    b = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    result = paired_difference(a, b)
    assert result["mean_diff"] > 0
    assert result["n"] == 8


def test_paired_difference_small_sample():
    result = paired_difference([0.5], [0.4])
    assert result["mean_diff"] is None
