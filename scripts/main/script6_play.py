import polars as pl

def script_lemma_reducible():

    # get etymology-less words
    df = pl.read_parquet('data/step2/ety_expanded.parquet')
    df = df.filter([
        (pl.col('num_templates') == 0)
        & pl.col('descendants').is_null()
    ]).with_columns([
        pl.struct([
            pl.col('word'),
            pl.col('lang_code').alias('lang'),
        ]).alias('etyless'),
    ])

    form_of = pl.read_parquet('data/parquet/spanish_forms_of.parquet')
    form_of = (
        form_of.with_columns([ # the host is inflected
            pl.struct([
                pl.col('host_word').alias('word'),
                pl.col('host_lang').alias('lang'),
            ]).alias('inflected'),
            pl.struct([ # the other word is the true lemma
                pl.col('other_word').alias('word'),
                pl.col('other_lang').alias('lang'),
            ]).alias('lemma_form'),
        ])
    )

    inflect_to_host = form_of.group_by('inflected').agg([
        pl.col('lemma_form')
    ]) # backwards: 1.149 million lemmas
    # 4.957 million inflected forms (some inflected can be decoded to multiple lemmas)

    inflect_to_one_host = inflect_to_host.filter([
        pl.col('lemma_form').list.len() == 1
    ]).with_columns([
        pl.col('lemma_form').list.get(0).alias('lemma_form'),
    ]) # .unnest(['lemma_form', 'inflected'])

    edges_df = pl.read_parquet('data/parquet/spanish_edges.parquet')

    # edges_df = edges_df.with_columns(
    #     pl.when(pl.col('is_desc')).then(pl.struct([
    #         pl.col('host_word').alias('older_word'),
    #         pl.col('host_lang').alias('older_lang'),
    #         pl.col('other_word').alias('younger_word'),
    #         pl.col('other_lang').alias('younger_lang'),
    #     ])).otherwise(pl.struct([
    #         pl.col('other_word').alias('older_word'),
    #         pl.col('other_lang').alias('older_lang'),
    #         pl.col('host_word').alias('younger_word'),
    #         pl.col('host_lang').alias('younger_lang'),
    #     ])).alias('youngins')
    # ).unnest('youngins')
    # .with_columns([
    #     pl.struct([
    #         pl.col('older_word').alias('word'),
    #         pl.col('older_lang').alias('lang'),
    #     ]).alias('older'),
    #     pl.struct([
    #         pl.col('younger_word').alias('word'),
    #         pl.col('younger_lang').alias('lang'),
    #     ]).alias('younger'),
    # ])


    # what's bad: when we have a dead end because in the edges_df, 
    # the older term refers to an inflected
    # form, and that inflected form does not have any etymology

    # bad_df = edges_df.join(inflect_to_one_host, left_on='older', right_on='inflected', how='inner')
    bad_df = edges_df.join(inflect_to_one_host, left_on=['other_word', 'other_lang'], 
                           right_on=[pl.col('inflected').struct.field('word'),
                                     pl.col('inflected').struct.field('lang')], how='inner')
    # bad_df = bad_df.join(df, left_on='lemma_form', right_on='etyless', how='inner')
    bad_df = bad_df.join(df, left_on=[pl.col('inflected').struct.field('word'), 
                                      pl.col('inflected').struct.field('lang')],
                         right_on=[pl.col('etyless').struct.field('word'), 
                                   pl.col('etyless').struct.field('lang')], how='inner')
    print(bad_df)

    # mostly false positives. not worth it.
    exit(0)

if __name__ == '__main__':
    print("Reading Parquet files...")
    script_lemma_reducible()
    # vertex_df = pl.read_parquet('data/step2/ety_expanded.parquet')
    

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