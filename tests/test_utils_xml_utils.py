import pytest

from feedtrail.utils import xml_utils


def test_clean_text_and_remove_invalid_chars():
    assert xml_utils.clean_text("  a\xa0 b &nbsp; c  ") == "a b c"
    assert xml_utils.clean_text("") == ""
    assert xml_utils.remove_invalid_xml_chars("a\x00b\x07c") == "abc"


def test_fix_attribute_ampersands_and_fix_xml_ampersands():
    src = "<x url=\"https://example.com?a=1&b=2\" href='/path?a=1&ok=2' />"
    fixed = xml_utils.fix_xml_ampersands(src)
    assert "a=1&amp;b=2" in fixed
    assert "/path?a=1&amp;ok=2" in fixed


def test_fix_content_detect_format_and_entity_sanitizers():
    noisy = "<rss><channel><title>x</title></channel></rss> junk"
    assert xml_utils.fix_content(noisy).endswith("</rss>")

    assert xml_utils.detect_format("<!doctype html><html></html>") == "html"
    assert xml_utils.detect_format("<?xml version='1.0'?><rss/>") == "xml"
    assert xml_utils.detect_format("plain text") == "unknown"

    simple = xml_utils.sanitize_xml_entities_simple("x & y <tag a='1&2'>z</tag>")
    assert simple == "x &amp; y <tag a='1&2'>z</tag>"

    strict = xml_utils.sanitize_xml_entities("x & y &amp; &#123; &#x1F;")
    assert strict == "x &amp; y &amp; &#123; &#x1F;"


def test_fix_escaped_cdata_markers_paths():
    assert xml_utils.fix_escaped_cdata_markers("") == ""

    already_real = "<![CDATA[safe]]>"
    assert xml_utils.fix_escaped_cdata_markers(already_real) == already_real

    escaped = "&lt;![CDATA[test]]&gt;"
    assert xml_utils.fix_escaped_cdata_markers(escaped) == "<![CDATA[test]]>"

    unchanged = "no markers here"
    assert xml_utils.fix_escaped_cdata_markers(unchanged) == unchanged


def test_extract_valid_xml_success_and_failure():
    text = "noise <rss><channel><title>x</title></channel></rss> tail"
    assert xml_utils.extract_valid_xml(text).startswith("<rss>")

    with pytest.raises(ValueError):
        xml_utils.extract_valid_xml("no tags at all")

    with pytest.raises(ValueError):
        xml_utils.extract_valid_xml("<rss><channel>", attempts=3)
