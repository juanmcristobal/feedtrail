"""Main module."""

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin

from feedtrail.utils.date_utils import auto_convert_date
from feedtrail.utils.xml_utils import (clean_text, extract_valid_xml,
                                       fix_content, fix_escaped_cdata_markers,
                                       sanitize_xml_entities)

IMG_TAG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


class FeedParser:
    def _find_text_element(self, parent, tag_name, ns):
        elem = parent.find(tag_name, ns)
        if elem is not None:
            return elem
        for child in parent:
            if child.tag.split("}")[-1] == tag_name.split(":")[-1]:
                return child
        return None

    def _get_inner_html(self, elem) -> str:
        if elem is None:
            return ""
        parts = []
        if elem.text:
            parts.append(elem.text)
        for child in list(elem):
            parts.append(ET.tostring(child, encoding="unicode"))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts)

    def _extract_categories(self, item, ns, namespace_prefix=None):
        elems = []
        if namespace_prefix:
            elems.extend(item.findall(f"{namespace_prefix}:category", ns))
        elems.extend(item.findall("category"))

        cats = []
        seen = set()
        for cat in elems:
            raw = cat.attrib.get("term")
            if not raw:
                raw = "".join(cat.itertext() or [])
            val = html.unescape((raw or "").strip())
            if val and val not in seen:
                seen.add(val)
                cats.append(val)
        return cats

    def _extract_author(self, item, ns, namespace_prefix=None):
        dc_elems = item.findall("dc:creator", ns)
        for el in dc_elems:
            txt = "".join(el.itertext() or []).strip()
            if txt:
                return html.unescape(txt)

        if namespace_prefix:
            author_elems = item.findall(f"{namespace_prefix}:author", ns)
            for a in author_elems:
                name = a.find(f"{namespace_prefix}:name", ns)
                if name is not None and name.text and name.text.strip():
                    return html.unescape(name.text.strip())
                txt = "".join(a.itertext() or []).strip()
                if txt:
                    return html.unescape(txt)

        for el in item.findall("author"):
            raw = "".join(el.itertext() or []).strip()
            if not raw:
                continue
            m = re.search(r"\(([^)]+)\)", raw)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
            return html.unescape(raw)

        return None

    def _extract_images(
        self, item, ns, base_url, namespace_prefix=None, description_html=None
    ):
        def iter_by_local(elem, localname):
            for child in elem.iter():
                if child.tag.split("}")[-1].lower() == localname.lower():
                    yield child

        seen = set()
        candidates = []

        def add(url):
            if not url:
                return
            url_abs = urljoin(base_url, url.strip())
            if url_abs and url_abs not in seen:
                seen.add(url_abs)
                candidates.append(url_abs)

        for enc in iter_by_local(item, "enclosure"):
            attrs = enc.attrib
            url = attrs.get("url") or attrs.get("href")
            mime_type = (attrs.get("type") or "").lower().strip()
            if url and (not mime_type or mime_type.startswith("image/")):
                add(url)

        for media_content in item.findall("media:content", ns):
            url = media_content.attrib.get("url")
            mime_type = (media_content.attrib.get("type") or "").lower().strip()
            if url and (not mime_type or mime_type.startswith("image/")):
                add(url)

        for media_thumb in item.findall("media:thumbnail", ns):
            url = media_thumb.attrib.get("url")
            if url:
                add(url)

        for link_elem in iter_by_local(item, "link"):
            rel = (link_elem.attrib.get("rel") or "").lower()
            href = link_elem.attrib.get("href") or link_elem.attrib.get("url")
            mime_type = (link_elem.attrib.get("type") or "").lower().strip()
            if (
                rel == "enclosure"
                and href
                and (not mime_type or mime_type.startswith("image/"))
            ):
                add(href)

        if description_html and not candidates:
            match = IMG_TAG_RE.search(description_html)
            if match:
                add(match.group(1))

        return candidates[0] if candidates else None

    def parse_feed_item(self, item, date_tags, base_url, namespace_prefix=None):
        if namespace_prefix:
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "media": "http://search.yahoo.com/mrss/",
                "content": "http://purl.org/rss/1.0/modules/content/",
                "dc": "http://purl.org/dc/elements/1.1/",
            }
        else:
            ns = {
                "content": "http://purl.org/rss/1.0/modules/content/",
                "media": "http://search.yahoo.com/mrss/",
                "dc": "http://purl.org/dc/elements/1.1/",
            }

        title_tag = f"{namespace_prefix}:title" if namespace_prefix else "title"
        title_elem = self._find_text_element(item, title_tag, ns)
        if title_elem is not None:
            raw_title = ""
            if namespace_prefix == "atom":
                ttype = (title_elem.attrib.get("type") or "").lower().strip()
                if ttype in ("html", "xhtml"):
                    raw_title = self._get_inner_html(title_elem)
                else:
                    raw_title = "".join(title_elem.itertext() or "")
            else:
                raw_title = "".join(title_elem.itertext() or "")
            unescaped_title = html.unescape(raw_title or "").strip()
            title = (
                clean_text(unescaped_title)
                if raw_title != unescaped_title
                else unescaped_title
            )
            title = title if title else None
        else:
            title = None

        link_tag = f"{namespace_prefix}:link" if namespace_prefix else "link"
        link_elem = self._find_text_element(item, link_tag, ns)
        link = None
        if link_elem is not None:
            if namespace_prefix:
                link = (link_elem.attrib.get("href") or "").strip() or None
            else:
                href = (
                    link_elem.attrib.get("href")
                    if hasattr(link_elem, "attrib")
                    else None
                )
                link = (href or (link_elem.text or "")).strip() or None
        if link:
            link = urljoin(base_url, link)
        else:
            guid = item.find("guid")
            if guid is not None and guid.text:
                gtxt = guid.text.strip()
                if gtxt.lower().startswith(("http://", "https://")):
                    link = urljoin(base_url, gtxt)

        if namespace_prefix:
            candidates = [f"{namespace_prefix}:content", f"{namespace_prefix}:summary"]
        else:
            candidates = ["content:encoded", "description", "content"]

        description_html = None
        for tag in candidates:
            el = self._find_text_element(item, tag, ns)
            if el is None:
                continue
            inner_html = self._get_inner_html(el).strip()
            if inner_html:
                description_html = html.unescape(inner_html)
                break

        description = clean_text(description_html).strip() if description_html else None

        summary = None
        summary_html = None
        if namespace_prefix == "atom":
            summary_elem = self._find_text_element(item, "atom:summary", ns)
            if summary_elem is not None:
                sum_type = (summary_elem.attrib.get("type") or "").lower().strip()
                if sum_type in ("html", "xhtml"):
                    sh = self._get_inner_html(summary_elem).strip()
                    if sh:
                        summary_html = html.unescape(sh)
                        summary = clean_text(summary_html).strip()
                else:
                    txt = "".join(summary_elem.itertext() or "")
                    if txt.strip():
                        summary = clean_text(html.unescape(txt)).strip()

        pub_date = None
        for date_tag in date_tags:
            search_tag = (
                f"{namespace_prefix}:{date_tag}" if namespace_prefix else date_tag
            )
            pub_elem = self._find_text_element(item, search_tag, ns)
            if pub_elem is not None and pub_elem.text and pub_elem.text.strip():
                iso = auto_convert_date(pub_elem.text.strip())
                if iso:
                    pub_date = iso
                    break

        categories = self._extract_categories(item, ns, namespace_prefix) or None
        author = self._extract_author(item, ns, namespace_prefix)
        image_url = self._extract_images(
            item,
            ns,
            base_url,
            namespace_prefix=namespace_prefix,
            description_html=description_html or summary_html,
        )

        return {
            "title": title,
            "link": link,
            "description": description,
            "summary": summary,
            "pub_date": pub_date,
            "author": author,
            "image": image_url,
            "categories": categories,
        }

    def parse_rss(self, root, base_url):
        channel = root.find("channel")
        headers = {}
        if channel is not None:
            for field in ["title", "link", "description"]:
                elem = channel.find(field)
                txt = elem.text.strip() if elem is not None and elem.text else ""
                if field == "title":
                    txt = clean_text(html.unescape(txt)) if txt else ""
                headers[field] = txt
            lb = channel.find("lastBuildDate")
            headers["updated"] = (
                auto_convert_date(lb.text.strip())
                if lb is not None and lb.text
                else None
            )
            lang = channel.find("language")
            headers["language"] = (
                lang.text.strip() if lang is not None and lang.text else "en-US"
            )
            gen = channel.find("generator")
            headers["generator"] = (
                html.unescape(gen.text.strip())
                if gen is not None and gen.text
                else None
            )

            parent_link_el = channel.find("link")
            parent_link = (
                urljoin(base_url, parent_link_el.text.strip())
                if parent_link_el is not None and parent_link_el.text
                else None
            )

            atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
            atom_self = channel.find('atom:link[@rel="self"]', atom_ns)
            self_link = (
                (atom_self.attrib.get("href") or "").strip()
                if atom_self is not None and atom_self.attrib.get("href")
                else None
            )

            headers["parent_link"] = parent_link
            headers["self_link"] = self_link
            headers["link"] = parent_link

        entry_base_url = headers.get("parent_link") or base_url

        items = []
        if channel is not None:
            for entry in channel.findall("item"):
                parsed = self.parse_feed_item(
                    entry, ["pubDate", "published", "updated"], entry_base_url
                )
                items.append(parsed)

            with_date = [it for it in items if it["pub_date"]]
            without_date = [it for it in items if not it["pub_date"]]
            with_date.sort(key=lambda x: x["pub_date"], reverse=True)

            items = with_date + without_date
            headers["updated"] = with_date[0]["pub_date"] if with_date else None

        return {"headers": headers, "items": items}

    def parse_atom(self, root, namespace, base_url):
        title_el = root.find("atom:title", namespace)
        if title_el is not None:
            ttype = (title_el.attrib.get("type") or "").lower().strip()
            if ttype in ("html", "xhtml"):
                raw_title = self._get_inner_html(title_el)
            else:
                raw_title = "".join(title_el.itertext() or "")
            header_title = clean_text(html.unescape(raw_title)).strip()
        else:
            header_title = ""

        any_link_el = root.find("atom:link", namespace)
        subtitle_el = root.find("atom:subtitle", namespace)
        if subtitle_el is not None:
            stype = (subtitle_el.attrib.get("type") or "").lower().strip()
            if stype in ("html", "xhtml"):
                raw_subtitle = self._get_inner_html(subtitle_el)
            else:
                raw_subtitle = "".join(subtitle_el.itertext() or "")
            unescaped_subtitle = html.unescape(raw_subtitle or "").strip()
            header_description = (
                clean_text(unescaped_subtitle)
                if raw_subtitle != unescaped_subtitle
                else unescaped_subtitle
            )
        else:
            header_description = ""

        headers = {
            "title": header_title,
            "link": (
                any_link_el.attrib.get("href", "").strip()
                if any_link_el is not None
                else ""
            ),
            "description": header_description,
            "updated": (
                auto_convert_date(
                    root.findtext(
                        "atom:updated", default="", namespaces=namespace
                    ).strip()
                )
                if root.findtext("atom:updated", namespaces=namespace)
                else None
            ),
            "language": (
                root.find("language").text.strip()
                if root.find("language") is not None and root.find("language").text
                else "en-US"
            ),
            "generator": (lambda _t: html.unescape(_t.strip()) if _t else None)(
                root.findtext("atom:generator", default="", namespaces=namespace)
            ),
        }

        parent_link = None
        self_link = None
        all_links = root.findall("atom:link", namespace)

        for link_el in all_links:
            href = (link_el.attrib.get("href") or "").strip()
            if not href:
                continue
            rel = (link_el.attrib.get("rel") or "").lower()
            if rel == "self" and not self_link:
                self_link = href
            elif (rel == "alternate" or not rel) and not parent_link:
                parent_link = href

        atom_id = (
            root.findtext("atom:id", default="", namespaces=namespace) or ""
        ).strip()

        def _looks_like_feed(url: str) -> bool:
            u = url.lower()
            return any(x in u for x in ("/feed", "/rss", "/atom", ".xml"))

        if atom_id.startswith(("http://", "https://")) and atom_id != self_link:
            if not parent_link or _looks_like_feed(parent_link):
                parent_link = atom_id

        if not parent_link:
            for link_el in all_links:
                href = (link_el.attrib.get("href") or "").strip()
                rel = (link_el.attrib.get("rel") or "").lower()
                if href and rel != "self":
                    parent_link = href
                    break

        if parent_link:
            parent_link = urljoin(base_url, parent_link)
        if self_link:
            self_link = urljoin(base_url, self_link)

        headers["parent_link"] = parent_link
        headers["self_link"] = self_link
        headers["link"] = parent_link

        entry_base_url = parent_link or base_url

        items = []
        for entry in root.findall("atom:entry", namespace):
            parsed = self.parse_feed_item(
                entry, ["updated", "published"], entry_base_url, "atom"
            )
            try:
                parsed["_sort_date"] = auto_convert_date(parsed["pub_date"])
            except Exception:
                parsed["_sort_date"] = datetime.min
            items.append(parsed)

        items.sort(key=lambda x: x["_sort_date"], reverse=True)
        for it in items:
            it.pop("_sort_date", None)

        headers["updated"] = items[0]["pub_date"] if items else None

        return {"headers": headers, "items": items}

    def _compute_request_hash(self, root: dict):
        try:
            normalized = json.dumps(root, ensure_ascii=False, sort_keys=True)
            return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        except Exception:
            return None

    def parse(self, xml_content: str, base_url: str = ""):
        try:
            xml_content = fix_escaped_cdata_markers(xml_content)
            content = sanitize_xml_entities(xml_content)
            valid = extract_valid_xml(content)
            fixed = fix_content(valid)
            root = ET.fromstring(fixed)

            if root.tag.lower() == "rss" or root.find("channel") is not None:
                parsed = self.parse_rss(root, base_url)
            else:
                parsed = self.parse_atom(
                    root, {"atom": "http://www.w3.org/2005/Atom"}, base_url
                )

            parsed["request_hash"] = self._compute_request_hash(parsed)
            return parsed

        except Exception as e:
            return {
                "headers": {},
                "items": [],
                "error": f"Feed processing error: {e}",
                "request_hash": None,
            }
