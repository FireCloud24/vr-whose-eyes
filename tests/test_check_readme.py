"""Tracing README numbers to results files, and the README's own rules."""
import re
from pathlib import Path

from scripts import check_readme

ROOT = Path(__file__).resolve().parents[1]


def test_numbers_in_finds_signed_decimals_percentages_and_thousands():
    text = "Share went from 5.30% to 5.45%, a change of -0.17 points (+0.03 later) over 43,028 rows."
    assert check_readme.numbers_in(text) == ["5.30%", "5.45%", "-0.17", "+0.03", "43,028"]


def test_normalise_ignores_format_but_keeps_a_minus_sign():
    assert check_readme.normalise("+0.33") == check_readme.normalise("0.33%") == "0.33"
    assert check_readme.normalise("1,000") == "1000"
    assert check_readme.normalise("-0.17") != check_readme.normalise("0.17")


def test_strip_non_prose_drops_code_comments_and_links():
    text = "Keep 7.\n```\npython x.py 99\n```\n<!-- MYO: write 2-4 -->\n[doc 3](results/file88.md) `cfg 55` https://a.b/66"
    assert check_readme.numbers_in(check_readme.strip_non_prose(text)) == ["7", "3"]


def test_trace_reports_found_known_and_missing():
    rows = check_readme.trace("In 2017 the effect was -0.17 over 1,000 users, not 0.99.",
                              {"a.md": "| -0.17 | 1000 |", "b.md": "users: 1,000"})
    by = {r["number"]: r for r in rows}
    assert by["2017"]["ok"] and "year" in by["2017"]["source"]
    assert by["-0.17"]["source"] == "results/a.md"
    assert by["1,000"]["source"] == "results/a.md, results/b.md"
    assert not by["0.99"]["ok"]
    assert "NOT FOUND" in check_readme.to_markdown(rows, 12)


def test_the_real_readme_is_fully_traced_and_follows_the_style_rules():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    results = {n: (ROOT / "results" / n).read_text(encoding="utf-8") for n in check_readme.SOURCES}
    rows = check_readme.trace(readme, results)
    assert [r["number"] for r in rows if not r["ok"]] == []
    prose = check_readme.strip_non_prose(readme)
    assert len(prose.split()) <= 1200
    assert "—" not in prose                                   # no em dashes
    for word in ("robust", "comprehensive", "honest", "leverage", "delve"):
        assert not re.search(rf"\b{word}", prose, flags=re.I), word
    for phrase in ("Short answer", "Skills shown", "Definition of done", "RQ1"):
        assert phrase not in readme
    assert "<!-- MYO: write 2–4 sentences on why you cared -->" in readme
    assert not re.search(r"\bnot\b[^.]{0,60}, but\b", prose)          # no "not X, but Y"
    assert "results/demo.gif" in readme and "results/chosen_vs_random.png" in readme


def test_every_file_the_readme_links_to_exists():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", readme):
        if not target.startswith("http"):
            assert (ROOT / target).exists(), target
