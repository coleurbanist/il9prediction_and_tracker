"""
inject_nav.py
─────────────
Adds <script src="nav.js"></script> to every .html file in the current
folder (or a specified folder), removing any existing nav.js script tag
first to avoid duplicates.

Usage:
    python inject_nav.py                   # process current directory
    python inject_nav.py path/to/folder    # process specific folder

The script only touches the <body> tag area — it does NOT rewrite the
entire file, so your existing page content is preserved.
"""

import os
import re
import sys

NAV_TAG = '<script src="nav.js"></script>'
HIDE_TAG = '<style>body{visibility:hidden!important}</style>'
# Pattern that matches any existing nav.js script tag (with or without path)
NAV_PATTERN = re.compile(r'<script[^>]+nav\.js[^>]*></script>', re.IGNORECASE)

folder = sys.argv[1] if len(sys.argv) > 1 else '.'
html_files = [f for f in os.listdir(folder) if f.lower().endswith('.html')]

if not html_files:
    print(f"No .html files found in '{folder}'")
    sys.exit(0)

for filename in sorted(html_files):
    path = os.path.join(folder, filename)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Remove existing nav.js tags
    content = NAV_PATTERN.sub('', content)

    # Insert before </body> (or at end of file if no </body>)
    if '</body>' in content.lower():
        content = re.sub(
            r'(</body>)',
            f'\n{NAV_TAG}\n\\1',
            content,
            flags=re.IGNORECASE,
            count=1,
        )
    else:
        content += f'\n{NAV_TAG}\n'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓  {filename}")

print(f"\nDone — {len(html_files)} file(s) updated.")
print("Make sure nav.js is in the same folder as your HTML files.")
