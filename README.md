# checkdmarc-web-frontend

The frontend project to the checkdmarc web application. The backend code is hosted in a [separate project](https://github.com/domainaware/checkdmarc-web-backend).

A live version can be found at [domaincheckup.net](https://domaincheckup.net).

## Features

Why create or use this when there are already so many other websites that check SPF and DMARC records?

- Responsive, mobile-first UI using Bootstrap
- Can be installed as a Progressive Web Application (PWA) on mobile devices and computers
- Provides all details from the [checkdmarc](https://domainaware.github.io/checkdmarc) library and CLI tool on a single page
  - DNSSEC validation
  - SPF
    - Record validation
    - Counting of DNS lookups and void lookups
    - Counting of lookups per mechanism
  - DMARC
    - Validation and parsing of DMARC records
    - Shows warnings when the DMARC record is made ineffective by `pct` or `sp` values
    - Checks for authorization records on reporting email addresses
  - BIMI
    - Validation of the mark format and certificate
    - Parsing of the mark certificate
  - MX records
    - Preference
    - IPv4 and IPv6 addresses
    - Checks for STARTTLS (optional; currently disabled on the production website)
    - Use of DNSSEC/TLSA/DANE to pin certificates
  - MTA-STS
    - Record parsing and validation
  - SMTP TLS Reporting (TLSRPT)
    - Record and policy parsing and validation
  - SOA record parsing
  - Nameserver listing
- No sales pitches
- Fully open source

## Running the web app locally

First, setup the backend server. Then, create a new python virtual environment and run `pip install -U -r requirements.txt`.

Configure the frontend using environment variables by copying `example.env` to `.env` and change the values.

Use the supplied example systemd `.service` file to create a systemd service, and use the example `nginx.conf` file to configure NGINX to serve it.

## Pull requests welcome

I have't done much frontend dev work, so any help is welcomed.
