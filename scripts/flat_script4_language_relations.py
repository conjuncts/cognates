"""Example usage with flat scripts: Understand """

import polars as pl

ety_df = pl.read_parquet('data/step3/ety_expanded_flat.parquet')
temp_df = pl.read_parquet('data/step3/templates_flat.parquet')
langcodes = pl.read_parquet('data/step3/langcodes_flat.parquet')
# Need: word lang, other lang
# Target: , see https://en.wiktionary.org/wiki/Template:derived#top
# der args.2 is the other language

applicable = temp_df.filter(
    pl.col('template_name').is_in(
        ['inherited', 'inh', 'inh+',
         # 'derived', 'der'
         ]) &
    (pl.col('key') == 'args.2') # ).str.len_chars() > 0)
)
applicable = applicable.pivot(
    index='entry_id', # ['entry_id', 'template_name'],
    on='key',
    values='value',
    aggregate_function='first'
)

# applicable = applicable.select('entry_id', 'item_number').unique()
applicable = applicable.join(ety_df.select(['entry_id', 'word', 'lang']), on='entry_id')

# join args.2 with langcodes
applicable = applicable.join(
    langcodes.select(['code', 'name']).rename({'code': 'args.2', 'name': 'origin_lang'}),
    on='args.2',
)
print(applicable)

# Now, examine relationships between languages
lang_relations = applicable
# .select(
#     'lang', 'origin_lang'
# )


# study what are most common origins for English? Latin? Proto-Italic?
en_relations = lang_relations.filter(pl.col('lang') == 'Proto-Italic')
en_relations = en_relations.group_by('origin_lang').len().sort('len', descending=True)
print(en_relations)

# ┌─────────────────────────┬───────┐
# │ origin_lang             ┆ count │
# │ ---                     ┆ ---   │
# │ str                     ┆ u32   │
# ╞═════════════════════════╪═══════╡
# │ Middle English          ┆ 24469 │
# │ Old English             ┆ 906   │
# │ Proto-Germanic          ┆ 46    │
# │ Northern Middle English ┆ 22    │
# │ Proto-West Germanic     ┆ 15    │
# │ …                       ┆ …     │
# │ Old French              ┆ 2     │
# │ Middle High German      ┆ 1     │
# │ Old Norse               ┆ 1     │
# │ Old Spanish             ┆ 1     │
# │ Late Latin              ┆ 1     │
# └─────────────────────────┴───────┘

# what are some weird ones?
reverse_relations = lang_relations.filter(
    (pl.col('origin_lang') == 'English')
    & (pl.col('lang') == 'Latin')
)
print(reverse_relations)