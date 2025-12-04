import json
import polars as pl
import os
from tqdm import tqdm

from etytreealg.graph.graph_construct import construct_forms_of_df, most_common_referenced_languages
from etytreealg.graph.graph_construct_flat import construct_edges_flat_df, construct_descendant_edges_flat_df
from etytreealg.graph.graph_io import hydrate_df

def probe_language_dependents():
    df = pl.read_parquet('data/step2/ety_expanded.parquet')
    df = df.with_row_index("index")
    print("Loaded!")
    df = hydrate_df(df)

    queries = ['en', 'la', 'es', 'de', 'fr', 'nl', 'it', 'pt', 'pl', 'ru', 'sv', 'no', 'da', 'is', 'ro']
    for q in queries:
        freqs = most_common_referenced_languages(df, q, hreadable=True, need_subset=True)
        with open(f'data/langfreqs/{q}_dependents.json', 'w') as f:
            json.dump(freqs, f, indent=2)
    exit(0)


def make_full_forms_of():
    df = pl.read_parquet('data/step2/ety_expanded.parquet')

    forms_of_df = construct_forms_of_df(df)
    forms_of_df.write_parquet('data/step4/forms_of.parquet')

    # print(forms_of_df)
    exit(0)


def main():
    # probe_language_dependents()

    # make_full_forms_of()
    df = pl.read_parquet('data/step3/ety_expanded_flat.parquet')

    # Ambitious goal: process *all* languages.

    templates_df = pl.read_parquet('data/step3/templates_flat.parquet')
    # weak_form_of_df = construct_related_edges_df(target_df)
    # print(weak_form_of_df)
    # exit(0)

    weak_edges_df = construct_edges_flat_df(df, templates_df) # need to find entry_id of peer
    # exit(0)


    desc_target_df = pl.read_parquet('data/step3/descendants_flat.parquet')
    weak_desc_edges_df = construct_descendant_edges_flat_df(df, desc_target_df)


    all_edges_df = pl.concat([weak_edges_df, weak_desc_edges_df])

    # 

    # .unique().sort("host_id").with_row_index("edge_id")


    # Now, recover the peer_id
    all_edges_df = all_edges_df.join(
        df.lazy().select(['entry_id', 'word', 'lang_code']).rename({
            'entry_id': 'peer_id',
        }).unique(["word", "lang_code"], keep="first"),
        left_on=['peer_word', 'peer_lang'],
        right_on=['word', 'lang_code'],
        how='left'
    ).collect()
    
    # now give edge_id. sort by host_id, keep order.
    all_edges_df = all_edges_df.sort(['host_id']).unique(maintain_order=True).with_row_index("edge_id")
    # vertex_df, edges_df = construct_adjacency_dfs(weak_edges_df)

    
    edges_dest = 'data/step4/weak_edges.parquet'

    all_edges_df.write_parquet(edges_dest)

if __name__ == "__main__":
    main()