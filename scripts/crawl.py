"""
Follow every link on the running site and report anything that isn't a 200.

Used by scripts/prodcheck.sh, where the point is not that the pages exist — the test
suite already covers that — but that they still render once DJANGO_DEBUG=0 changes how
static files are named and how errors are handled. A template referencing an asset that
isn't in the manifest raises at render time, which is a 500 no test sees if the test
never renders the page in production mode.

    python3 scripts/crawl.py http://localhost:8080/

Stays on the site's own host, follows href and src alike so stylesheets and scripts are
checked too, and exits non-zero if anything failed.
"""

import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

LINK = re.compile(rb'(?:href|src)="([^"]+)"')
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")


def crawl(base):
    seen, queue, broken = set(), [base], []
    host = urlparse(base).netloc

    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        request = urllib.request.Request(url, headers={"User-Agent": "prodcheck"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                body = response.read()
                content_type = response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            broken.append((str(error.code), url))
            continue
        except Exception as error:  # noqa: BLE001 - any failure to fetch is a failure
            broken.append((type(error).__name__, url))
            continue

        if status != 200:
            broken.append((str(status), url))
        if content_type not in ("text/html", "application/xhtml+xml"):
            continue

        for raw in LINK.findall(body):
            link = raw.decode("utf-8", "replace")
            if link.startswith(SKIP_SCHEMES):
                continue
            target = urljoin(url, link).split("#")[0]
            if urlparse(target).netloc == host and target not in seen:
                queue.append(target)

    return seen, broken


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
    seen, broken = crawl(base)

    if broken:
        print(f"{len(broken)} of {len(seen)} urls failed")
        for status, url in broken:
            print(f"  {status}  {url}")
        return 1

    print(f"{len(seen)} urls, all 200")
    return 0


if __name__ == "__main__":
    sys.exit(main())
