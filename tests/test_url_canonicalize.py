"""Tests for URL canonicalization used in search dedupe."""

from src.graph.nodes.search import canonicalize_url


def test_canonicalize_strips_www_and_slash():
    assert (
        canonicalize_url("https://WWW.Example.com/path/")
        == "https://example.com/path"
    )


def test_canonicalize_empty():
    assert canonicalize_url("") == ""
