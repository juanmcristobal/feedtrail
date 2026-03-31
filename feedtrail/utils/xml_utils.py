import re
import xml.etree.ElementTree as ET


# Cleans up extra whitespace and replaces non-breaking spaces in text
def clean_text(text):
    if text:
        text = text.replace("\xa0", " ").replace("&nbsp;", " ")
        return re.sub(r"\s+", " ", text).strip()
    return ""


# Removes characters that are invalid in XML (control characters)
def remove_invalid_xml_chars(text):
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)


# Fixes ampersands in a specific attribute by replacing illegal & with &amp;
def fix_attribute_ampersands(xml_str, attr_name):
    def repl(match: re.Match[str]) -> str:
        quote = match.group(1)
        attr_value = match.group(2)
        fixed_value = re.sub(
            r"&(?!amp;|lt;|gt;|apos;|quot;|#[0-9]+;|#x[0-9a-fA-F]+;)",
            "&amp;",
            attr_value,
        )
        return f"{attr_name}={quote}{fixed_value}{quote}"

    # Support both single-quoted and double-quoted attributes.
    return re.sub(rf"""{attr_name}=(["'])(.*?)\1""", repl, xml_str)


# Applies ampersand fixing to both `url` and `href` attributes
def fix_xml_ampersands(xml_str):
    xml_str = fix_attribute_ampersands(xml_str, "url")
    xml_str = fix_attribute_ampersands(xml_str, "href")
    return xml_str


# Trims malformed content after </rss> or </feed>, removes invalid chars and fixes ampersands
def fix_content(xml_string):
    rss_end = xml_string.find("</rss>")
    atom_end = xml_string.find("</feed>")
    if rss_end != -1:
        xml_string = xml_string[: rss_end + 6]
    elif atom_end != -1:
        xml_string = xml_string[: atom_end + 7]
    xml_string = remove_invalid_xml_chars(xml_string)
    xml_string = fix_xml_ampersands(xml_string)
    return xml_string


# Detects if the content is HTML, XML, or unknown based on starting tags
def detect_format(text):
    text = text.strip().lower()
    if text.startswith("<!doctype html") or "<html" in text:
        return "html"
    elif (
        text.startswith("<?xml") or text.startswith("<rss") or text.startswith("<feed")
    ):
        return "xml"
    else:
        return "unknown"


# Naively replaces & with &amp; only outside of tags (not used in production)
def sanitize_xml_entities_simple(text):
    parts = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
            parts.append(char)
        elif char == ">":
            in_tag = False
            parts.append(char)
        elif not in_tag and char == "&":
            parts.append("&amp;")
        else:
            parts.append(char)
    return "".join(parts)


# Replaces any & character not part of a valid XML entity with &amp;
def sanitize_xml_entities(text):
    """
    Replaces '&' characters that are not part of a valid XML entity with '&amp;'.
    Valid XML entities are:
    - one of the 5 XML predefined named entities (e.g. &amp;)
    - & followed by # and digits and ending in ; (e.g. &#123;)
    - & followed by #x and hex digits and ending in ; (e.g. &#x1F;)
    """
    # Important: HTML named entities like '&nbsp;' are NOT valid XML unless a DTD defines them.
    # If we treat all named entities as valid, strict XML parsers will fail with "undefined entity".
    pattern = re.compile(r"&(?!((amp|lt|gt|apos|quot)|#[0-9]+|#x[0-9A-Fa-f]+);)")
    return pattern.sub("&amp;", text)


def fix_escaped_cdata_markers(text: str) -> str:
    """
    Some fetchers/browser layers return XML with the CDATA markers escaped, e.g.
      &lt;![CDATA[Dark Web Informer]]&gt;
    which makes the markers show up literally in parsed titles/descriptions.

    If present, unescape only the CDATA section delimiters (not the full document)
    to preserve existing entities like &amp;.
    """
    if not text:
        return text
    # If the document already contains real CDATA blocks, do not touch anything.
    # Unescaping stray ']]&gt;' inside CDATA/HTML content can accidentally introduce ']]>'
    # which prematurely closes CDATA and breaks the XML.
    if "<![CDATA[" in text or "]]>" in text:
        return text

    # Only rewrite when we see the escaped wrapper start marker. This avoids touching
    # unrelated occurrences of ']]&gt;' in content.
    if re.search(r"&lt;!\[CDATA\[", text, flags=re.IGNORECASE) is None:
        return text

    # Be conservative: only touch the delimiter patterns.
    text = re.sub(r"&lt;!\[CDATA\[", "<![CDATA[", text, flags=re.IGNORECASE)
    text = re.sub(r"\]\]&gt;", "]]>", text, flags=re.IGNORECASE)
    return text


# Attempts to extract a valid XML string by trimming noisy input
def extract_valid_xml(text, attempts=30):
    stripped = text.strip()
    start = stripped.find("<")
    end = stripped.rfind(">") + 1

    if start == -1 or end == -1 or start >= end:
        raise ValueError("No valid XML structure with < and > found.")

    candidate = stripped[start:end]

    def is_valid_xml(xml_string):
        try:
            ET.fromstring(xml_string)
            return True
        except ET.ParseError:
            return False

    for attempt in range(attempts):
        if is_valid_xml(candidate):
            return candidate

        # Alternate trimming: end on even attempts, start on odd
        if attempt % 2 == 0:
            candidate = candidate[:-1]
        else:
            candidate = candidate[1:]

    raise ValueError("Could not extract a valid XML segment after multiple attempts.")
