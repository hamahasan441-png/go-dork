"""Pytest configuration — restrict test collection to test_*.py files."""

collect_ignore = [
    "scanner.py",
    "dorker.py",
    "crawler.py",
    "dorkmaker.py",
    "app.py",
    "urlvalidation.py",
]
