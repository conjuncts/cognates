import polars as pl
import io
_actually_starts_with_asterisk = pl.read_csv(io.StringIO("""word,lang,lang_code
*,Translingual,mul
*,Translingual,mul
*,English,en
*,German,de
*nix,English,en
*nices,English,en
*nixes,English,en
*band,English,en
*bands,English,en
* *,Translingual,mul
*69,English,en
*69,English,en
*69,French,fr
*69,Spanish,es
*fg*,German,de
*69s,English,en
*69ing,English,en
*69ed,English,en
*rsch,German,de
*rschl*ch,German,de
*`lowbar`*,Translingual,mul
*NSYNCer,English,en
*NSYNCers,English,en
* * *,Translingual,mul
* * *,Translingual,mul
**,Translingual,mul
*67ed,English,en
*67ing,English,en
*67s,English,en
*67,English,en
*67,English,en
"""))

def _reproduce_asterisk(df):
    
    """
    Reproduce _actually_starts_with_asterisk: the exceptions where the word actually starts with *, but is not a reconstruction.
    """
    df.filter(
        pl.col('word').str.starts_with('*'), # latin word does not have macron.
        # pl.col('lang').str.contains('Latin')
    )[['word', 'lang']]
