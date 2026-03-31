import re
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from dateutil import parser
from dateutil.parser import UnknownTimezoneWarning
from dateutil.tz import gettz

warnings.filterwarnings("ignore", category=UnknownTimezoneWarning)


def auto_convert_date(date_string, output_format="%Y-%m-%dT%H:%M:%S"):
    if not date_string or not isinstance(date_string, str):
        return None

    s = date_string.strip()

    # Normaliza espacios y offsets con dos puntos: "-04:00" -> "-0400"
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"([+-]\d{2}):(\d{2})(?!\d)", r"\1\2", s)  # -04:00 -> -0400
    s = re.sub(r"\bZ\b", "+0000", s)  # Z -> +0000 para strptime

    tzinfos = {
        # USA
        "EST": gettz("America/New_York"),
        "EDT": gettz("America/New_York"),
        "CST": gettz("America/Chicago"),
        "CDT": gettz("America/Chicago"),
        "MST": gettz("America/Denver"),
        "MDT": gettz("America/Denver"),
        "PST": gettz("America/Los_Angeles"),
        "PDT": gettz("America/Los_Angeles"),
        # Europa
        "GMT": gettz("Etc/GMT"),
        "UTC": gettz("UTC"),
        "WET": gettz("Europe/Lisbon"),
        "WEST": gettz("Europe/Lisbon"),
        "CET": gettz("Europe/Paris"),
        "CEST": gettz("Europe/Paris"),
        "EET": gettz("Europe/Athens"),
        "EEST": gettz("Europe/Athens"),
        "BST": gettz("Europe/London"),
        # Asia/Oceanía
        "MSK": gettz("Europe/Moscow"),
        "IST": gettz("Asia/Kolkata"),
        "HKT": gettz("Asia/Hong_Kong"),
        "JST": gettz("Asia/Tokyo"),
        "AWST": gettz("Australia/Perth"),
        "ACST": gettz("Australia/Adelaide"),
        "ACDT": gettz("Australia/Adelaide"),
        "AEST": gettz("Australia/Sydney"),
        "AEDT": gettz("Australia/Sydney"),
        "NZST": gettz("Pacific/Auckland"),
        "NZDT": gettz("Pacific/Auckland"),
    }

    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _format(dt: datetime) -> str:
        return dt.strftime(output_format)

    # 1) RFC 2822/1123 (ideal para RSS/Atom estilo email)
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            dt = _to_utc(dt)
            # Opcional: tope para futuras
            now_utc = datetime.now(timezone.utc)
            if dt > now_utc:
                dt = now_utc
            return _format(dt)
    except Exception:
        pass

    # 2) strptime con formatos comunes (incluye RFC 2822 con %z)
    common_formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M %z",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %Z",
    ]
    for fmt in common_formats:
        try:
            dt = datetime.strptime(s, fmt)
            dt = _to_utc(dt)
            now_utc = datetime.now(timezone.utc)
            if dt > now_utc:
                dt = now_utc
            return _format(dt)
        except ValueError:
            continue

    # 2.5) EXTRA: extrae un substring "Month DD, YYYY" o "DD Month YYYY" y parsea eso
    month_names = (
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    )
    patterns = [
        rf"{month_names}\s+\d{{1,2}},\s*\d{{4}}",  # May 29, 2025
        rf"\d{{1,2}}\s+{month_names}\s+\d{{4}}",  # 29 May 2025
        rf"{month_names}\s+\d{{1,2}}\s+\d{{4}}",  # May 29 2025 (sin coma)
    ]
    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            try:
                dt = parser.parse(m.group(0), fuzzy=False, tzinfos=tzinfos)
                dt = _to_utc(dt)
                now_utc = datetime.now(timezone.utc)
                if dt > now_utc:
                    dt = now_utc
                return _format(dt)
            except Exception:
                pass

    # 3) dateutil (muy flexible)
    try:
        dt = parser.parse(s, fuzzy=True, tzinfos=tzinfos)
        dt = _to_utc(dt)
        now_utc = datetime.now(timezone.utc)
        if dt > now_utc:
            dt = now_utc
        return _format(dt)
    except Exception:
        pass

    # 4) Último intento: trozo RFC 2822 con offset y volver a intentar
    m = re.search(
        r"[A-Za-z]{3}, \d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{2}:?\d{2}",
        s,
    )
    if m:
        chunk = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", m.group(0))
        try:
            dt = datetime.strptime(chunk, "%a, %d %b %Y %H:%M:%S %z")
            dt = _to_utc(dt)
            now_utc = datetime.now(timezone.utc)
            if dt > now_utc:
                dt = now_utc
            return _format(dt)
        except Exception:
            pass

    return None
