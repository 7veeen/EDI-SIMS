import os
import re

for root, dirs, files in os.walk('frontend'):
    for file in files:
        if file.endswith(('.js', '.html')):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for idx, line in enumerate(f, 1):
                    # Remove JavaScript template string interpolations ${...}
                    clean = re.sub(r'\$\{[^}]*\}', '', line)
                    if '$' in clean:
                        print(f"{path}:{idx}: {line.strip()[:120]}")
