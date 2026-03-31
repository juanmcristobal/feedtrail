import hashlib
import xml.etree.ElementTree as ET

from feedtrail.feed_parser import FeedParser

RSS_WITH_NAMESPACES = """\
<rss version="2.0"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:atom="http://www.w3.org/2005/Atom"
     xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>My &amp; Feed</title>
    <link>https://example.com/blog</link>
    <description>Site description</description>
    <lastBuildDate>Wed, 20 Mar 2024 10:00:00 GMT</lastBuildDate>
    <language>es-ES</language>
    <generator>Generator &amp; Co</generator>
    <atom:link rel="self" href="/feed.xml" />
    <item>
      <title>First &amp; Item</title>
      <link>/post-1</link>
      <description><![CDATA[Hello <img src="/desc.jpg"/> world]]></description>
      <pubDate>Wed, 20 Mar 2024 09:00:00 GMT</pubDate>
      <category term="security" />
      <category>security</category>
      <category>threat-intel</category>
      <dc:creator>Alice &amp; Bob</dc:creator>
      <enclosure url="/media.jpg" type="image/jpeg" />
    </item>
    <item>
      <title>Second</title>
      <guid>https://example.com/post-2</guid>
      <description>Plain content</description>
      <author>Staff (Bob)</author>
      <pubDate>not-a-date</pubDate>
      <enclosure url="/file.pdf" type="application/pdf" />
    </item>
  </channel>
</rss>
"""


ATOM_WITH_NAMESPACES = """\
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:media="http://search.yahoo.com/mrss/">
  <title type="html">&lt;b&gt;Atom Feed&lt;/b&gt;</title>
  <subtitle type="html">&lt;i&gt;Atom Description&lt;/i&gt;</subtitle>
  <updated>2024-03-20T12:00:00Z</updated>
  <generator>Atom &amp; Generator</generator>
  <id>https://example.com/site</id>
  <link rel="self" href="/atom.xml" />
  <link rel="alternate" href="/site" />
  <entry>
    <title type="html">&lt;strong&gt;Entry A&lt;/strong&gt;</title>
    <link href="/a" />
    <summary type="html">&lt;p&gt;Summary A&lt;/p&gt;</summary>
    <updated>2024-03-20T11:00:00Z</updated>
    <category term="cat-a" />
    <author><name>Ana</name></author>
    <media:thumbnail url="/thumb-a.jpg" />
  </entry>
  <entry>
    <title>Entry B</title>
    <link href="/b" />
    <summary>Summary B</summary>
    <published>2024-03-19T11:00:00Z</published>
    <author>Team (Carlos)</author>
  </entry>
</feed>
"""


def test_parse_rss_end_to_end_and_sorting():
    parser = FeedParser()
    parsed = parser.parse(RSS_WITH_NAMESPACES, base_url="https://example.com")

    assert parsed["headers"]["title"] == "My & Feed"
    assert parsed["headers"]["link"] == "https://example.com/blog"
    assert parsed["headers"]["parent_link"] == "https://example.com/blog"
    assert parsed["headers"]["self_link"] == "/feed.xml"
    assert parsed["headers"]["language"] == "es-ES"
    assert parsed["headers"]["generator"] == "Generator & Co"
    assert parsed["headers"]["updated"] == parsed["items"][0]["pub_date"]

    first = parsed["items"][0]
    assert first["title"] == "First & Item"
    assert first["link"] == "https://example.com/post-1"
    assert first["description"] == 'Hello <img src="/desc.jpg"/> world'
    assert first["author"] == "Alice & Bob"
    assert first["categories"] == ["security", "threat-intel"]
    assert first["image"] == "https://example.com/media.jpg"

    second = parsed["items"][1]
    assert second["title"] == "Second"
    assert second["link"] == "https://example.com/post-2"
    assert second["author"] == "Bob"
    assert second["pub_date"] is None

    assert len(parsed["request_hash"]) == 64


def test_parse_atom_end_to_end_and_link_resolution():
    parser = FeedParser()
    parsed = parser.parse(ATOM_WITH_NAMESPACES, base_url="https://example.com")

    assert parsed["headers"]["title"] == "<b>Atom Feed</b>"
    assert parsed["headers"]["description"] == "<i>Atom Description</i>"
    assert parsed["headers"]["parent_link"] == "https://example.com/site"
    assert parsed["headers"]["self_link"] == "https://example.com/atom.xml"
    assert parsed["headers"]["generator"] == "Atom & Generator"
    assert parsed["headers"]["updated"] == parsed["items"][0]["pub_date"]

    first = parsed["items"][0]
    assert first["title"] == "<strong>Entry A</strong>"
    assert first["summary"] == "<p>Summary A</p>"
    assert first["author"] == "Ana"
    assert first["categories"] == ["cat-a"]
    assert first["image"] == "https://example.com/thumb-a.jpg"


def test_helpers_cover_fallback_branches():
    parser = FeedParser()
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }
    item = ET.fromstring(
        """\
        <item xmlns:atom="http://www.w3.org/2005/Atom"
              xmlns:media="http://search.yahoo.com/mrss/"
              xmlns:dc="http://purl.org/dc/elements/1.1/">
          <atom:title type="text">X</atom:title>
          <category term="alpha" />
          <category>alpha</category>
          <category>beta</category>
          <author>Ops Team</author>
          <link rel="enclosure" href="/fallback.jpg" type="image/jpeg" />
        </item>
        """
    )

    title = parser._find_text_element(item, "atom:title", ns)
    assert title is not None
    assert parser._find_text_element(item, "title", {}) is not None
    assert parser._find_text_element(item, "missing", ns) is None
    assert parser._get_inner_html(None) == ""
    mixed = ET.fromstring("<title>Hello<b>x</b>tail</title>")
    assert parser._get_inner_html(mixed) == "Hello<b>x</b>tailtail"
    assert parser._extract_categories(item, ns) == ["alpha", "beta"]
    assert parser._extract_author(item, ns) == "Ops Team"
    assert parser._extract_author(ET.fromstring("<item />"), ns) is None
    multi_author = ET.fromstring(
        "<item><author> </author><author>Team (Eve)</author></item>"
    )
    assert parser._extract_author(multi_author, ns) == "Eve"
    assert (
        parser._extract_images(
            ET.fromstring("<item><description>x</description></item>"),
            ns,
            "https://example.com",
            description_html='<img src="/from-desc.jpg"/>',
        )
        == "https://example.com/from-desc.jpg"
    )
    assert (
        parser._extract_images(item, ns, "https://example.com")
        == "https://example.com/fallback.jpg"
    )


def test_parse_rss_without_channel_and_parse_error_path(monkeypatch):
    parser = FeedParser()
    root = ET.fromstring("<rss></rss>")
    parsed = parser.parse_rss(root, "https://example.com")
    assert parsed == {"headers": {}, "items": []}

    monkeypatch.setattr(
        "feedtrail.feed_parser.extract_valid_xml",
        lambda _: (_ for _ in ()).throw(ValueError("bad")),
    )
    broken = parser.parse("<rss><channel>")
    assert broken["items"] == []
    assert broken["request_hash"] is None
    assert "Feed processing error" in broken["error"]


def test_compute_request_hash_paths():
    parser = FeedParser()
    good = {"a": 1, "b": "x"}
    digest = parser._compute_request_hash(good)
    expected = hashlib.sha256(b'{"a": 1, "b": "x"}').hexdigest()
    assert digest == expected

    assert parser._compute_request_hash({"bad": {1, 2}}) is None


def test_parse_atom_sort_date_exception_branch(monkeypatch):
    parser = FeedParser()
    root = ET.fromstring(
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>x</title></entry></feed>'
    )
    namespace = {"atom": "http://www.w3.org/2005/Atom"}

    monkeypatch.setattr(
        parser,
        "parse_feed_item",
        lambda *_args, **_kwargs: {"title": "x", "pub_date": "2024-01-01T00:00:00"},
    )
    monkeypatch.setattr(
        "feedtrail.feed_parser.auto_convert_date",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("x")),
    )

    parsed = parser.parse_atom(root, namespace, "https://example.com")
    assert parsed["items"][0]["title"] == "x"


def test_parse_feed_item_missing_title_and_media_content_image():
    parser = FeedParser()
    item = ET.fromstring(
        """\
        <item xmlns:media="http://search.yahoo.com/mrss/">
          <link>/item</link>
          <enclosure type="image/jpeg" />
          <media:content url="/media-content.jpg" type="image/png" />
          <description>desc</description>
        </item>
        """
    )
    parsed = parser.parse_feed_item(item, ["pubDate"], "https://example.com")
    assert parsed["title"] is None
    assert parsed["image"] == "https://example.com/media-content.jpg"


def test_parse_atom_parent_link_fallback_variants():
    parser = FeedParser()
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    root_from_id = ET.fromstring(
        """\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Atom Plain</title>
          <subtitle>Subtitle Plain</subtitle>
          <id>https://example.com/home</id>
          <link rel="self" href="/atom.xml" />
          <link rel="alternate" />
          <entry><title>a</title></entry>
        </feed>
        """
    )
    parsed_from_id = parser.parse_atom(root_from_id, ns, "https://example.com")
    assert parsed_from_id["headers"]["parent_link"] == "https://example.com/home"
    assert parsed_from_id["headers"]["title"] == "Atom Plain"
    assert parsed_from_id["headers"]["description"] == "Subtitle Plain"

    root_from_non_self = ET.fromstring(
        """\
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>x</title>
          <link rel="self" href="/self.xml" />
          <link rel="related" href="/related" />
        </feed>
        """
    )
    parsed_from_non_self = parser.parse_atom(
        root_from_non_self, ns, "https://example.com"
    )
    assert (
        parsed_from_non_self["headers"]["parent_link"] == "https://example.com/related"
    )
