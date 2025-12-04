import polars as pl


df = pl.read_parquet("data/step5/edges.parquet").group_by(
    "template_name"
).agg(
    pl.count().alias("count")
).sort("count", descending=True)
for name, count in df.select(["template_name", "count"]).iter_rows():
    print(f"{name}: {count}")