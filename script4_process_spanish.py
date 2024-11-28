import polars as pl
import os
from tqdm import tqdm

from etytreealg.decode.decode_templates import get_langcodes_and_words
from etytreealg.decode.decode_words import decode_word
from etytreealg.graph.graph_construct import construct_edges_df, construct_adjacency_dfs
from etytreealg.graph.graph_io import hydrate_df


def main():
    df = pl.read_parquet('data/parquet/ety_expanded.parquet')
    df = df.with_row_index("index")
    print("Loaded!")
    df = hydrate_df(df)

    target_langs = """Latin
    English
    Spanish
    Old Spanish
    Ancient Greek
    Late Latin
    Medieval Latin
    Vulgar Latin
    Proto-Indo-European

    French
    Italian
    Portuguese

    German
    Proto-Germanic
    Proto-West Germanic

    Middle French
    Old French

    Middle English
    Old English

    Arabic
    Old Norse""".split("\n")
    target_langs = [x.strip() for x in target_langs if x]
    target_langcodes = "la,en,es,osp,grc,LL.,ML.,VL.,ine-pro,fr,it,pt,de,gem-pro,gmw-pro,frm,fro,enm,ang,ar,non".split(",")


    target_df = df.filter(
        pl.col("lang").is_in(target_langs) &
        (pl.col("num_templates") > 0)
    )

    edges_dest = 'data/parquet/spanish_edges.parquet'
    vertex_dest = 'data/parquet/spanish_vertices.parquet'
    if os.path.exists(edges_dest):
        edges_df = pl.read_parquet(edges_dest)
        vertex_df = pl.read_parquet(vertex_dest)

    else:
        weak_edges_df = construct_edges_df(target_df)
        vertex_df, edges_df = construct_adjacency_dfs(weak_edges_df)
        edges_df.write_parquet(edges_dest)
        vertex_df.write_parquet(vertex_dest)

if __name__ == "__main__":
    main()