import json
import polars as pl
import os
from tqdm import tqdm

from etytreealg.graph.graph_construct import construct_descendant_edges_df, construct_edges_df, construct_adjacency_dfs, most_common_referenced_languages
from etytreealg.graph.graph_io import hydrate_df

def probe_language_dependents():
    df = pl.read_parquet('data/parquet/ety_expanded.parquet')
    df = df.with_row_index("index")
    print("Loaded!")
    df = hydrate_df(df)

    queries = ['en', 'la', 'es', 'de', 'fr', 'nl', 'it', 'pt', 'pl', 'ru', 'sv', 'no', 'da', 'is', 'ro']
    for q in queries:
        freqs = most_common_referenced_languages(df, q, hreadable=True, need_subset=True)
        with open(f'data/langfreqs/{q}_dependents.json', 'w') as f:
            json.dump(freqs, f, indent=2)
    exit(0)

    

def main():
    # probe_language_dependents()

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
    Old Norse
    
    Catalan
    Basque
    Galician
    Classical Nahuatl
    
    High German
    Low German
    Old High German
    Middle Low German
    German Low German
    Middle High German
    Germanic
    North Germanic
    Old Saxon

    Dutch
    Middle Dutch
    Old Dutch
    Dutch Low Saxon""".split("\n")
    target_langs = [x.strip() for x in target_langs if x]
    # target_langcodes = "la,en,es,osp,grc,LL.,ML.,VL.,ine-pro,fr,it,pt,de,gem-pro,gmw-pro,frm,fro,enm,ang,ar,non".split(",")

    # tempted to add: Catalan, Basque, Galician, Classical Nahuatl

    desc_target_df = df.filter(
        (pl.col("lang").is_in(target_langs)
        #  | pl.col("lang_code").str.starts_with('roa-')
         ) &
        (pl.col("descendants_h").is_not_null())
    )
    weak_desc_edges_df = construct_descendant_edges_df(desc_target_df)

    # exit(0)

    target_df = df.filter(
        (pl.col("lang").is_in(target_langs)
        #  | pl.col("lang_code").str.starts_with('roa-')
         ) &
        (pl.col("num_templates") > 0)
    )

    weak_edges_df = construct_edges_df(target_df)

    all_edges_df = pl.concat([weak_edges_df, weak_desc_edges_df])
    # vertex_df, edges_df = construct_adjacency_dfs(weak_edges_df)
    vertex_df, edges_df, desc_edges_df = construct_adjacency_dfs(all_edges_df) weak_edges_df, weak_desc_edges_df)

    desc_edges_dest = 'data/parquet/spanish_desc_edges.parquet'
    edges_dest = 'data/parquet/spanish_edges.parquet'
    vertex_dest = 'data/parquet/spanish_vertices.parquet'
    
    # desc_edges_dest = 'data/parquet/german_desc_edges.parquet'
    # edges_dest = 'data/parquet/german_edges.parquet'
    # vertex_dest = 'data/parquet/german_vertices.parquet'

    desc_edges_df.write_parquet(desc_edges_dest)
    edges_df.write_parquet(edges_dest)
    vertex_df.write_parquet(vertex_dest)

if __name__ == "__main__":
    main()