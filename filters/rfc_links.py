# filters/rfc_links.py
from __future__ import annotations

import re
from markupsafe import Markup, escape

__all__ = ["link_rfc"]

# --- Main matcher: RFC or draft; optional ", §/section <section>" ------------
CITATION = re.compile(
    r"""
    (?<!\w)                                   # don't match mid-word
    (?:
        RFC \s* (?P<rfc>\d+)                  # RFC number: RFC 5322 / RFC5322
      | (?P<draft>draft-[A-Za-z0-9][A-Za-z0-9-]*?(?:-\d{2})?)  # draft name
    )
    (?:
        \s*,?\s*
        (?:
            §{1,2} |                          # § or §§
            section
        )
        \s*
        (?P<section>                          # conservative section capture
            [^\s\]\),;:.]+
            (?:\.[^\s\]\),;:.]+)*
            (?:-[^\s\]\),;:.]+)*
        )
    )?                                        # <-- section is optional
    (?=[\s\]\),;:.]|$)                        # stop at typical terminators/EOL
    """,
    re.IGNORECASE | re.VERBOSE,
)

# --- Helper patterns (precompiled) -------------------------------------------
RE_NUMERIC_SECTION = re.compile(r"\A\d+(?:\.\d+)*\Z")  # 3.4.5
RE_APPENDIX_SECTION = re.compile(r"\A([A-Za-z])(?:\.(\d+(?:\.\d+)*))?\Z")
RE_NONALNUM = re.compile(r"[^A-Za-z0-9]+")
RE_COLLAPSE_WS = re.compile(r"\s+")
RE_TRAILING_PUNCT = re.compile(r"[).,;: ]+$")  # trim end junk


def _rfc_anchor(section: str) -> str:
    """
    Map a section string to datatracker's HTML fragment:
      - "4.1.2" -> section-4.1.2
      - "A"     -> appendix-a
      - "A.1.2" -> appendix-a-1-2
      - fallback -> section-<slug>
    """
    s = RE_TRAILING_PUNCT.sub("", section.strip())

    if RE_NUMERIC_SECTION.fullmatch(s):
        return f"section-{s}"

    m = RE_APPENDIX_SECTION.fullmatch(s)
    if m:
        head = m.group(1).lower()
        tail = (m.group(2) or "").replace(".", "-")
        return f"appendix-{head}{('-' + tail) if tail else ''}"

    slug = RE_NONALNUM.sub("-", s).strip("-").lower()
    return f"section-{slug}"


def _replacement(m: re.Match) -> str:
    rfc = m.group("rfc")
    draft = m.group("draft")
    raw_section = m.group("section")

    if raw_section:
        # Normalize whitespace and trim trailing punctuation for the anchor
        section = RE_COLLAPSE_WS.sub(" ", raw_section)
        section = RE_TRAILING_PUNCT.sub("", section)
        fragment = "#" + _rfc_anchor(section)
    else:
        # No section: link to the document root (no fragment)
        section = None
        fragment = ""

    if rfc:
        base = f"https://datatracker.ietf.org/doc/html/rfc{rfc}"
    else:
        base = f"https://datatracker.ietf.org/doc/html/{draft.lower()}"

    # Preserve the original matched text as the link text (already escaped)
    visible = m.group(0)

    return f'<a href="{base}{fragment}">{visible}</a>'


def link_rfc(value: str) -> Markup:
    """
    Turn RFC/draft citations into datatracker links.

    Examples recognized:
      - RFC 5322
      - (RFC 7489)
      - RFC9116 section 2.1.2.
      - RFC 7489, § A.1
      - draft-ietf-dmarc-base-11 § 4.2
      - draft-kucherawy-dkim-crypto-02 section A.1
    """
    # Escape entire input first; then safely inject <a> tags via substitution.
    return Markup(CITATION.sub(_replacement, escape(value)))
