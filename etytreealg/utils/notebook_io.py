import polars as pl
import json
def load_df():
    df_dest = '../data/step2/ety_expanded.parquet'
    return pl.read_parquet(df_dest)

from etytreealg.graph.graph_io import hydrate_df