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
    - Counting of lookups per include
  - DMARC
    - Validation and parsing of DMARC records
    - Shows warnings when the DMARC record is made ineffective by `pct` or `sp` values
    - Checks for authorization records on reporting email addresses
  - MX records
    - Preference
    - IPv4 and IPv6 addresses
    - Checks for STARTTLS (optional; currently disabled on the production website)
    - Use of DNSSEC/TLSA/DANE to pin certificates
  - SMTP-STS
  - SMTP TLS reporting
    - Record and policy parsing and validation
    - Record validation and parsing
  - SOA record parsing
  - Nameserver listing
- No sales pitches
- Fully open source
