import os
import re

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

def audit_currency():
    findings = []
    dollar_regex = re.compile(r'\$([0-9]|{\s*(?:[a-zA-Z0-9_\.]*(?:price|amount|val|total|cost|subtotal|balance|payment)[a-zA-Z0-9_\.]*)\s*})', re.IGNORECASE)
    literal_dollar_regex = re.compile(r'(\$\s*\d+|\bUSD\b|\bDollar\b)', re.IGNORECASE)

    for root, dirs, files in os.walk(FRONTEND_DIR):
        for f in files:
            if f.endswith(('.js', '.html')):
                path = os.path.join(root, f)
                rel_path = os.path.relpath(path, FRONTEND_DIR)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    for idx, line in enumerate(fp, 1):
                        # skip if line only contains template string without currency meaning, e.g. `${...}`
                        # we look for '$' that is not part of '${' OR is '${' for an amount/price
                        if '$' in line:
                            # check if it has '$' followed by digits, or '$' before '${'
                            if re.search(r'\$\d', line) or re.search(r'\$\${', line) or re.search(r'\$ \${', line) or re.search(r'\$\s*<', line) or re.search(r'>\s*\$', line):
                                findings.append((rel_path, idx, line.strip()))
                            elif 'USD' in line or 'Dollar' in line or 'dollar' in line:
                                findings.append((rel_path, idx, line.strip()))

    print(f"Total potential USD/Dollar currency occurrences found: {len(findings)}")
    for f, l, content in findings:
        print(f"  {f}:{l}: {content[:100]}")

if __name__ == "__main__":
    audit_currency()
