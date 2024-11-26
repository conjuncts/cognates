"""
Expand the https://github.com/tatuylonen/wiktextract/ dump.
raw-wiktextract-data.json.gz
"""

import gzip
import json

def read_jsongz(filepath):
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)

if __name__ == '__main__':
    for j, item in enumerate(read_jsongz('D:/etytreealg/raw-wiktextract-data.json.gz')):
        print(item)
        print()
        print()
        if j > 100:
            break