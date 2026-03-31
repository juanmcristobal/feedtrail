<p align="center">
  <img src="banner-header.png" alt="feedtrail banner" width="100%">
</p>

# FeedTrail

Feed Tracking and Retrieval Abstraction Interface Layer.

`feedtrail` provides a resilient RSS/Atom parser focused on production-style feeds where XML can be noisy, partially malformed, or inconsistent across publishers.

Repository: https://github.com/juanmcristobal/feedtrail

## What It Does

- Parses RSS and Atom feeds with namespace support.
- Normalizes and cleans feed/item text content.
- Converts heterogeneous date formats to UTC ISO strings.
- Extracts structured metadata: title, link, description, summary, author, categories, and primary image.
- Computes a deterministic `request_hash` for parsed payload integrity checks.
- Handles malformed XML defensively (entity sanitization, escaped CDATA recovery, trailing content trimming).

## Installation

```bash
pip install feedtrail
```


## Quick Start

```python
from feedtrail.feed_parser import FeedParser

xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <link>https://example.com</link>
    <description>Demo</description>
    <item>
      <title>Hello</title>
      <link>/hello</link>
      <pubDate>Wed, 20 Mar 2024 09:00:00 GMT</pubDate>
      <description><![CDATA[Post body]]></description>
    </item>
  </channel>
</rss>"""

parser = FeedParser()
result = parser.parse(xml_content, base_url="https://example.com")

print(result["headers"]["title"])
print(result["items"][0]["link"])
```

## Output Contract

`FeedParser.parse(...)` returns a dictionary with:

- `headers`: feed-level metadata (`title`, `link`, `description`, `updated`, `language`, `generator`, `parent_link`, `self_link`).
- `items`: list of normalized entries, each including:
  - `title`
  - `link`
  - `description`
  - `summary`
  - `pub_date` (ISO-like UTC string, when available)
  - `author`
  - `image`
  - `categories`
- `request_hash`: SHA-256 hash of normalized parsed payload.
- `error`: present when parsing fails (`items` will be empty in that case).


## Support & Connect

* ⭐ **Star the repo** if you found it useful
* ☕ **Support me:** Say thanks by buying me a coffee! [https://buymeacoffee.com/juanmcristobal](https://buymeacoffee.com/juanmcristobal)
* 💼 **Open to work:** [https://www.linkedin.com/in/jmcristobal/](https://www.linkedin.com/in/jmcristobal/)


## Author

- Juan Manuel Cristóbal Moreno (<juanmcristobal@gmail.com>)

See [AUTHORS.md](AUTHORS.md) for contributors.
