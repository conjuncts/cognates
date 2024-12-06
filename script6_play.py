import polars as pl

if __name__ == '__main__':
    print("Reading Parquet files...")
    # vertex_df = pl.read_parquet('data/parquet/ety_expanded.parquet')
    

    # of_interest = vertex_df.filter(
    #     (pl.col('lang_code') == 'LL.') |
    #     (pl.col('lang_code').str.starts_with('la-')) |
    #     (pl.col('lang') == 'Late Latin') |
    #     (pl.col('lang') == 'Vulgar Latin')
    #     # (pl.col('word').str.contains('rzi'))
    #     # (pl.col('word').str.contains('erzi$'))
    # ).unique(['word', 'lang_code']).sort('word')

    edges_df = pl.read_parquet('data/parquet/checkpoints/spanish_edges.parquet')

    of_interest = edges_df.filter(
        (pl.col('parent_lang') == 'LL.') |
        (pl.col('parent_lang').str.starts_with('la-'))
    )
    print(of_interest)