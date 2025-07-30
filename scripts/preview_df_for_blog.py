import polars as pl

# Compare and contrast flattened/unflattened nested JSON
df = pl.scan_parquet('data/step2/ety_expanded.parquet').select(
    'templates'
).with_row_index('entry_id').filter(pl.col('templates').is_not_null())
df = df.head(5).collect()
print(df.head(5).to_pandas().to_markdown())

df2 = pl.scan_parquet('data/step3/templates_flat.parquet').collect()

# take the same entry_id
df2 = df2.filter(pl.col('entry_id').is_in(df['entry_id']))
print(df2.to_pandas().to_markdown(index=False))


# example flattening
bookstore = {
  "storeName": "The Reading Nook",
  "location": "123 Main St, Fictionville",
  "inventory": [
    {
      "id": "B001",
      "title": "The Art of Code",
      "author": "Jane Developer",
      "price": 29.99,
      "ratings": {
        "average": 4.5,
        "reviews": 134
      }
    },
    {
      "id": "B002",
      "title": "Mystery at Midnight",
      "author": "Samantha Sleuth",
      "price": 15.5,
      "ratings": {
        "average": 4.0,
        "reviews": 89
      }
    },
  ]
}

def flat_iter_dict(d, parent_key='', sep='.'):
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            yield from flat_iter_dict(v, new_key, sep=sep)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    yield from flat_iter_dict(item, f"{new_key}[{i}]", sep=sep)
                else:
                    yield f"{new_key}[{i}]", item
        else:
            yield new_key, v

collector = [(k, v) for k, v in flat_iter_dict(bookstore)]
flattened_df = pl.DataFrame(collector, schema=['key', 'value'], orient='row')
print(flattened_df.to_pandas().to_markdown(index=False))