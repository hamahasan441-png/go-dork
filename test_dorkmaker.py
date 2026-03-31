"""Tests for dorkmaker module — dork query builder."""

import pytest

from dorkmaker import build_query, OPERATORS, TEMPLATES


class TestBuildQuery:
    """Tests for the build_query function."""

    # ------------------------------------------------------------------
    # Single operator
    # ------------------------------------------------------------------

    def test_single_operator_no_spaces(self):
        parts = [{"operator": "site", "value": "example.com"}]
        assert build_query(parts) == "site:example.com"

    def test_single_operator_with_spaces_auto_quoted(self):
        parts = [{"operator": "intitle", "value": "admin panel"}]
        assert build_query(parts) == 'intitle:"admin panel"'

    def test_single_operator_already_quoted(self):
        parts = [{"operator": "intitle", "value": '"admin panel"'}]
        assert build_query(parts) == 'intitle:"admin panel"'

    # ------------------------------------------------------------------
    # Multiple operators
    # ------------------------------------------------------------------

    def test_multiple_operators(self):
        parts = [
            {"operator": "site", "value": "example.com"},
            {"operator": "inurl", "value": "admin"},
        ]
        assert build_query(parts) == "site:example.com inurl:admin"

    def test_three_operators(self):
        parts = [
            {"operator": "site", "value": "example.com"},
            {"operator": "intitle", "value": "login"},
            {"operator": "filetype", "value": "php"},
        ]
        assert build_query(parts) == "site:example.com intitle:login filetype:php"

    # ------------------------------------------------------------------
    # Negation
    # ------------------------------------------------------------------

    def test_negation(self):
        parts = [{"operator": "site", "value": "example.com", "negate": True}]
        assert build_query(parts) == "-site:example.com"

    def test_negation_with_spaces(self):
        parts = [{"operator": "intitle", "value": "admin panel", "negate": True}]
        assert build_query(parts) == '-intitle:"admin panel"'

    def test_negation_false(self):
        parts = [{"operator": "site", "value": "example.com", "negate": False}]
        assert build_query(parts) == "site:example.com"

    # ------------------------------------------------------------------
    # Plain keywords (no/unknown operator)
    # ------------------------------------------------------------------

    def test_plain_keyword(self):
        parts = [{"operator": "", "value": "password"}]
        assert build_query(parts) == "password"

    def test_plain_keyword_with_spaces(self):
        parts = [{"operator": "", "value": "admin login"}]
        assert build_query(parts) == '"admin login"'

    def test_unknown_operator_treated_as_keyword(self):
        parts = [{"operator": "nonexistent", "value": "test"}]
        assert build_query(parts) == "test"

    def test_missing_operator_key(self):
        parts = [{"value": "test"}]
        assert build_query(parts) == "test"

    # ------------------------------------------------------------------
    # Empty / skipped values
    # ------------------------------------------------------------------

    def test_empty_value_skipped(self):
        parts = [{"operator": "site", "value": ""}]
        assert build_query(parts) == ""

    def test_whitespace_value_skipped(self):
        parts = [{"operator": "site", "value": "   "}]
        assert build_query(parts) == ""

    def test_mixed_empty_and_valid(self):
        parts = [
            {"operator": "site", "value": ""},
            {"operator": "inurl", "value": "admin"},
        ]
        assert build_query(parts) == "inurl:admin"

    def test_empty_parts_list(self):
        assert build_query([]) == ""

    # ------------------------------------------------------------------
    # Combined / complex queries
    # ------------------------------------------------------------------

    def test_complex_query(self):
        parts = [
            {"operator": "site", "value": "example.com"},
            {"operator": "inurl", "value": "admin"},
            {"operator": "filetype", "value": "pdf"},
            {"operator": "", "value": "confidential"},
            {"operator": "site", "value": "other.org", "negate": True},
        ]
        expected = 'site:example.com inurl:admin filetype:pdf confidential -site:other.org'
        assert build_query(parts) == expected

    def test_negated_keyword(self):
        parts = [{"operator": "", "value": "spam", "negate": True}]
        assert build_query(parts) == "-spam"

    # ------------------------------------------------------------------
    # All known operators
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("op", OPERATORS.keys())
    def test_all_operators_produce_output(self, op):
        parts = [{"operator": op, "value": "test"}]
        result = build_query(parts)
        assert result == f"{op}:test"


class TestOperatorsData:
    """Verify integrity of the OPERATORS dict."""

    def test_operators_not_empty(self):
        assert len(OPERATORS) > 0

    @pytest.mark.parametrize("op", OPERATORS.keys())
    def test_operator_has_required_keys(self, op):
        for key in ("description", "example", "placeholder"):
            assert key in OPERATORS[op], f"Operator '{op}' missing key '{key}'"

    @pytest.mark.parametrize("op", OPERATORS.keys())
    def test_operator_example_contains_operator(self, op):
        assert op in OPERATORS[op]["example"]


class TestTemplatesData:
    """Verify integrity of the TEMPLATES dict."""

    def test_templates_not_empty(self):
        assert len(TEMPLATES) > 0

    @pytest.mark.parametrize("category", TEMPLATES.keys())
    def test_template_category_has_queries(self, category):
        assert len(TEMPLATES[category]) > 0

    @pytest.mark.parametrize("category", TEMPLATES.keys())
    def test_template_queries_are_strings(self, category):
        for q in TEMPLATES[category]:
            assert isinstance(q, str)
            assert len(q) > 0
