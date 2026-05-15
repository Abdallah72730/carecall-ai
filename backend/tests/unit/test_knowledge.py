"""Unit tests for services/knowledge.py pure formatting functions."""
from __future__ import annotations

from services.knowledge import format_all_faqs, format_context


def test_format_all_faqs_empty():
    assert format_all_faqs([]) == ""


def test_format_all_faqs_single():
    faqs = [{"question": "Are you open Sunday?", "answer": "No.", "category": "hours"}]
    result = format_all_faqs(faqs)
    assert "[hours]" in result
    assert "Q: Are you open Sunday?" in result
    assert "A: No." in result


def test_format_all_faqs_groups_by_category():
    faqs = [
        {"question": "Q1", "answer": "A1", "category": "billing"},
        {"question": "Q2", "answer": "A2", "category": "hours"},
        {"question": "Q3", "answer": "A3", "category": "billing"},
    ]
    result = format_all_faqs(faqs)
    billing_pos = result.index("[billing]")
    hours_pos = result.index("[hours]")
    assert billing_pos < hours_pos  # sorted alphabetically
    assert result.count("[billing]") == 1  # grouped, not repeated


def test_format_all_faqs_missing_category_defaults_to_general():
    faqs = [{"question": "Q?", "answer": "A.", "category": ""}]
    result = format_all_faqs(faqs)
    assert "[general]" in result


def test_format_context_empty():
    assert format_context([]) == ""


def test_format_context_single():
    faqs = [{"question": "Q?", "answer": "A."}]
    result = format_context(faqs)
    assert "Q: Q?" in result
    assert "A: A." in result


def test_format_context_multiple():
    faqs = [
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
    ]
    result = format_context(faqs)
    assert "Q: Q1" in result
    assert "Q: Q2" in result
    # Separated by blank line
    assert "\n\n" in result
