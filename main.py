#!/usr/bin/env python

import os
import re
import unicodedata

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, Response

ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")  # includes ZWSP, ZWNJ, ZWJ, BOM

load_dotenv()

required_env_vars = ["SITE_TITLE", "BACKEND_URL", "BACKEND_API_KEY"]
for var in required_env_vars:
    if var not in os.environ:
        print(f"The required environment variable {var} is missing.")
        exit(1)

site_title = os.environ["SITE_TITLE"]
backend_url = os.environ["BACKEND_URL"].strip("/")
backend_api_key = os.environ["BACKEND_API_KEY"]
check_smtp_tls = None
if "CHECK_SMTP_TLS" in os.environ:
    check_smtp_tls = os.environ["CHECK_SMTP_TLS"]


app = Flask(__name__)


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
def show_home():
    return render_template("index.html.jinja", site_title=site_title)


@app.post("/")
def redirect_to_domain_page():
    domain = normalize_domain(request.form["domain"])
    return redirect(f"/domain/{domain}")


@app.route("/domain/<domain>")
def domain(domain):
    domain = normalize_domain(domain)
    get_params = {"api_key": backend_api_key}
    if check_smtp_tls:
        get_params["check_smtp_tls"] = check_smtp_tls
    results = requests.get(f"{backend_url}/domain/{domain}", params=get_params).json()
    if (
        "error" in results["soa"]
        and "does not exist" in results["soa"]["error"].lower()
    ):
        content = render_template(
            "domain-does-not-exist.html.jinja", site_title=site_title, domain=domain
        )
        return Response(content, status=404)
    return render_template(
        "domain.html.jinja", site_title=site_title, domain=domain, results=results
    )
