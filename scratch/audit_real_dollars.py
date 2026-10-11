import os
import re

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

def audit_real_dollars():
    findings = []
    # Match '$' NOT followed by '{' OR '$$' (e.g. '$${')
    pattern = re.compile(r'(\$\s*\d+|\$\${|\$\s*<|>[^<]*\$|\bUSD\b|\bdollar[s]?\b)', re.IGNORECASE)

    for root, dirs, files in os.walk(FRONTEND_DIR):
        for f in files:
            if f.endswith(('.js', '.html')):
                path = os.path.join(root, f)
                rel_path = os.path.relpath(path, FRONTEND_DIR)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    for idx, line in enumerate(fp, 1):
                        # Filter out normal JS template strings like `${...}`
                        line_clean = line
                        # replace all '${...}' with ''
                        # but if it has '$${' that leaves '$'
                        line_without_templates = re.sub(r'(?<!\$)\${[^}]*}', '', line)
                        if '$' in line_without_templates or 'USD' in line_without_templates or re.search(r'\bdollar[s]?\b', line_without_templates, re.I):
                            # verify it's not a regex or comment
                            if not line.strip().startswith('//') and not line.strip().startswith('*'):
                                findings.append((rel_path, idx, line.strip()))

    print(f"ACTUAL DOLLAR CURRENCY OCCURRENCES: {len(findings)}")
    for f, l, content in findings:
        print(f"  {f}:{l}: {content}")

if __name__ == "__main__":
    audit_real_dollars()
