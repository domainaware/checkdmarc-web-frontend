#!/usr/bin/env python

import os
import re
import time
import unicodedata
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from markupsafe import Markup, escape


ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")  # includes ZWSP, ZWNJ, ZWJ, BOM
RFC_CITATION = re.compile(
    r"""
    (?<!\w)                         # don't match inside a larger word
    RFC\s* (?P<rfc>\d+)            # RFC number
    \s*,?\s*
    (?:
        §{1,2} |                    # "§" or "§§"
        section                     # or "section"
    )
    \s*
    (?P<section>                    # capture section text conservatively
        [^\s\]\),;:.]+              # token (e.g., 3.6.1 or A.1)
        (?:\.[^\s\]\),;:.]+)*       # allow further .parts
        (?:-[^\s\]\),;:.]+)*        # allow hyphen bits (rare)
    )
    (?=[\s\]\),;:.]|$)              # stop before terminators/EOL
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _rfc_anchor(section: str) -> str:
    """
    Map a section string to rfc-editor HTML anchors:
      - "4.1.2"     -> section-4.1.2
      - "A", "A.1"  -> appendix-a, appendix-a-1
    Fallback: slug under 'section-...'
    """
    s = section.strip().rstrip(").,;:")  # defensive trim

    if re.fullmatch(r"\d+(?:\.\d+)*", s):  # numeric chain
        return f"section-{s}"

    m = re.fullmatch(r"([A-Za-z])(?:\.(\d+(?:\.\d+)*))?", s)
    if m:  # appendix style
        head = m.group(1).lower()
        tail = (m.group(2) or "").replace(".", "-")
        return f"appendix-{head}{('-' + tail) if tail else ''}"

    # Fallback: conservative slug (rare in RFCs but safe)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return f"section-{slug}"


def link_rfc(value: str) -> Markup:
    """
    Replace all RFC citations in the text with <a> links to rfc-editor.org.
    Input is fully escaped first; only our injected <a> tags are trusted.
    """

    def _repl(m: re.Match) -> str:
        rfc = m.group("rfc")
        # normalize whitespace + strip trailing punctuation from the section
        raw_section = m.group("section")
        section = re.sub(r"\s+", " ", raw_section).rstrip(").,;: ")
        fragment = _rfc_anchor(section)
        url = f"https://www.rfc-editor.org/rfc/rfc{rfc}.html#{fragment}"
        visible = f"RFC {rfc} § {escape(section)}"
        return f'<a href="{url}">{visible}</a>'

    return Markup(RFC_CITATION.sub(_repl, escape(value)))


load_dotenv()

required_env_vars = [
    "SITE_NAME",
    "BACKEND_URL",
    "SITE_OWNER",
    "SITE_OWNER_URL",
    "BACKEND_API_KEY",
]
missing_env_vars = []
for var in required_env_vars:
    if var not in os.environ:
        missing_env_vars.append(var)
if len(missing_env_vars):
    print(f"Error: Missing required environment variables {",".join(missing_env_vars)}")
    exit(1)

site_name = os.environ["SITE_NAME"]
site_owner = os.environ["SITE_OWNER"]
site_owner_url = os.environ["SITE_OWNER_URL"]
backend_url = os.environ["BACKEND_URL"].strip("/")
backend_api_key = os.environ["BACKEND_API_KEY"]
check_smtp_tls = os.getenv("CHECK_SMTP_TLS")
if check_smtp_tls:
    check_smtp_tls = check_smtp_tls.lower() in ["true", 1]

app = Flask(__name__)
app.jinja_env.filters["link_rfc"] = link_rfc

if app.debug is False:
    app.config.update(
        PREFERRED_URL_SCHEME="https",  # so url_for(..., _external=True) uses https
    )


@app.context_processor
def inject_common_vars():
    vars = {
        "site_name": site_name,
        "site_owner": site_owner,
        "site_owner_url": site_owner_url,
        "debug": app.debug,
    }
    return vars


@app.errorhandler(404)
def not_found():
    render_template("not-found.html.jinja"), 404


@app.errorhandler(500)
def internal_error():
    render_template("internal-error.html.jinja"), 500


@app.template_global()
def canonical_url() -> str:
    """
    Build a canonical absolute URL for the current endpoint (no querystring).
    Falls back to request.base_url if endpoint/view_args missing.
    """
    try:
        if request.endpoint:
            return url_for(
                request.endpoint, **(request.view_args or {}), _external=True
            )
    except Exception:
        pass
    # Fallback: strip query/fragment from current URL
    parts = list(urlsplit(request.url))
    parts[3] = ""  # query
    parts[4] = ""  # fragment
    return urlunsplit(parts)


@app.before_request
def start_timer():
    request.start_time = time.perf_counter()


def normalize_domain(domain: str) -> str:
    """
    Normalize an input domain by removing zero-width characters and lowering it

    Args:
        domain (str): A domain or subdomain

    Returns:
        str: A normalized domain
    """
    # 1. Normalize Unicode (NFC form for consistency)
    domain = unicodedata.normalize("NFC", domain)
    # 2. Remove zero-width and similar hidden chars
    domain = ZERO_WIDTH_RE.sub("", domain)
    # 3. Lowercase for case-insensitivity (domains are case-insensitive)
    return domain.lower()


@app.get("/")
def index():
    return render_template(
        "index.html.jinja",
    )


@app.post("/")
def redirect_to_domain_page():
    domain = normalize_domain(request.form["domain"])
    return redirect(f"/domain/{domain}")


@app.route("/domain/<domain>")
def domain(domain):
    sample_domains = [
        # Basic example
        "example.com",
        # Proton has everything configured correctly (declined BIMI)
        "proton.me",
        # Gmail oddly has DMARC sp=none
        "gmail.com",
        # Yahoo currently has MTA-STS in testing
        "yahoo.com",
        # change.org has a valid BIMI image with a mark certificate
        "change.org",
    ]
    is_sample_domain = domain in sample_domains

    start_time = getattr(request, "start_time", time.perf_counter())
    domain = normalize_domain(domain)
    get_params = {"api_key": backend_api_key}
    if check_smtp_tls:
        get_params["check_smtp_tls"] = check_smtp_tls
    results = requests.get(f"{backend_url}/domain/{domain}", params=get_params)
    if results.status_code == 400:
        return render_template("not-a-domain.html.jinja", domain=domain), 400
    results = results.json()
    elapsed_time = round(time.perf_counter() - start_time, 3)
    if (
        "error" in results["soa"]
        and "does not exist" in results["soa"]["error"].lower()
    ):
        render_template(
            "domain-does-not-exist.html.jinja",
            domain=domain,
            is_sample_domain=is_sample_domain,
            elapsed_time=elapsed_time,
        ), 404

    return render_template(
        "domain.html.jinja", domain=domain, results=results, elapsed_time=elapsed_time
    )
