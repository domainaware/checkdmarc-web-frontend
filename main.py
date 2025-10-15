#!/usr/bin/env python

import os
import re
import time
import unicodedata
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for

from filters.rfc_links import link_rfc


ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")  # includes ZWSP, ZWNJ, ZWJ, BOM

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
def not_found(error):
    return render_template("error.html.jinja", error="Not found"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html.jinja", error="Internal error"), 500


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
        error = f"{domain} is not a domain"
        return render_template("error.html.jinja", error=error), 400
    results = results.json()
    elapsed_time = round(time.perf_counter() - start_time, 3)
    if (
        "error" in results["soa"]
        and "does not exist" in results["soa"]["error"].lower()
    ):
        error = f"{domain} does not exist"
        return (
            render_template("error.html.jinja", error=error),
            404,
        )

    return render_template(
        "domain.html.jinja",
        domain=domain,
        results=results,
        is_sample_domain=is_sample_domain,
        elapsed_time=elapsed_time,
    )
