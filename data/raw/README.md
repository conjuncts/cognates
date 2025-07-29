Some dumps need to be downloaded by hand. In particular, 

## raw Mediawiki dump

- Can be found at https://dumps.wikimedia.org/enwiktionary/
- place in `data/raw/enwiktionary-20240501-pages-articles.xml.bz2`
- Used for step 1
- It is symlinked to `D:/sandisk/etytreealg/enwiktionary-20240501-pages-articles.xml.bz2`

## wiktextract dump (tatuylonen)

- Use the https://github.com/tatuylonen/wiktextract/ dump.
- place in `data/raw/raw-wiktextract-data.json.gz`
- Used for step 2 and beyond
- I used the one from `2024/5/5`, which was up-to-date at the time.
- It is symlinked to `D:/sandisk/etytreealg/raw-wiktextract-data.json.gz`