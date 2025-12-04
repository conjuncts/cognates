import json
import polars as pl
import os
from tqdm import tqdm

from etytreealg.graph.graph_construct_flat import construct_edges_flat_df, construct_descendant_edges_flat_df, construct_forms_of_flat_df



def main():
    # probe_language_dependents()

    # make_full_forms_of()
    df = pl.read_parquet('data/step3/ety_expanded_flat.parquet')

    # Ambitious goal: process *all* languages.

    templates_df = pl.read_parquet('data/step3/templates_flat.parquet')
    # weak_form_of_df = construct_related_edges_df(target_df)
    # print(weak_form_of_df)
    # exit(0)
    print("Making lemma edges...")
    weak_lemma_df = construct_forms_of_flat_df(df)

    print("Making descendant edges...")
    desc_target_df = pl.read_parquet('data/step3/descendants_flat.parquet')
    weak_desc_edges_df = construct_descendant_edges_flat_df(df, desc_target_df)

    print("Making direct edges...")
    weak_edges_df = construct_edges_flat_df(df, templates_df) # need to find entry_id of peer
    # exit(0)

    all_edges_df = pl.concat([weak_lemma_df, weak_edges_df, weak_desc_edges_df], how='diagonal_relaxed').collect()

    # 

    # .unique().sort("host_id").with_row_index("edge_id")


    # Note: no need to recover peer_id,
    # Because we need to give unassigned (word, langcode) a new ID late anyways (will have to redo)

    # all_edges_df = all_edges_df.join(
    #     df.lazy().select(['entry_id', 'word', 'lang_code']).rename({
    #         'entry_id': 'peer_id',
    #     }).unique(["word", "lang_code"], keep="first"),
    #     left_on=['peer_word', 'peer_lang'],
    #     right_on=['word', 'lang_code'],
    #     how='left'
    # ).collect()
    
    # now give edge_id. sort by host_id, keep order.
    all_edges_df = all_edges_df.sort(['host_id']).unique(maintain_order=True).with_row_index("edge_id")
    # vertex_df, edges_df = construct_adjacency_dfs(weak_edges_df)

    # rearrange: host_id, peer_id, template_name, ...rest

    # all_edges_df = all_edges_df.select([
    #     'edge_id', 'host_id', 'peer_id', 'template_name',
    #     'peer_word', 'peer_lang', 'palt_word', 'palt_lang', 'edge_type'
    # ])
    
    edges_dest = 'data/step4/weak_edges.parquet'

    all_edges_df.write_parquet(edges_dest)

if __name__ == "__main__":
    main()