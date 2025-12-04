
import polars as pl
def make_vertices():
    """
    Create vertices.

    How is this different from before?
    - entry_id: entry in Wiktionary
    - entry_id: one word can have multiple etymology entries, definitions, etc.
    - unassigned words: some edges point to words that don't have definitions in Wiktionary.
    We need to assign a vert_id for those as well.
    - vert_id: (word, langcode) pair uniquely defines a vertex.
    - so one vert_id can map to multiple entry_ids (or None, for unassigned words).
    """

    entry_df = pl.scan_parquet("data/step3/ety_expanded_flat.parquet").select(
        "entry_id",
        "word",
        # "lang",
        "lang_code",
        # "ety"        
    )
    # .filter(
        # pl.col("word").str.strip_chars().str.len_chars() > 0
    # )
    
    word_df = entry_df.group_by("word", "lang_code", maintain_order=True).agg(
        pl.col("entry_id")
    ).with_row_index("vert_id").explode("entry_id").collect()
    

    max_vert_id = word_df.select(pl.col("vert_id").max()).item()
    print(f"Max vert_id: {max_vert_id}")

    weak_edges_df = pl.read_parquet("data/step4/weak_edges.parquet")
    if 'peer_id' in weak_edges_df.columns:
        unassigned_df = weak_edges_df.filter(
            pl.col("peer_id").is_null()
        ).select("peer_word", "peer_lang").unique(maintain_order=True)
    else:
        unassigned_df = weak_edges_df.select("peer_word", "peer_lang").join(
            word_df.select("word", "lang_code"),
            left_on=["peer_word", "peer_lang"],
            right_on=["word", "lang_code"],
            how="anti"
        )
    unassigned_df= unassigned_df.rename({
        "peer_word": "word",
        "peer_lang": "lang_code"
    }).with_columns(
        pl.lit(None).alias("entry_id")
    ).with_row_index("vert_id", offset=max_vert_id + 1)

    full_vert_df = pl.concat([word_df, unassigned_df], how="diagonal")
    full_vert_df.write_parquet("data/step4/vertices.parquet")


def make_edges():
    vert_df = pl.read_parquet("data/step4/vertices.parquet")
    weak_edges = pl.read_parquet("data/step4/weak_edges.parquet")

    # convert usage of entry_id to vert_id
    wordlang2vert = vert_df.select(
        "vert_id", "word", "lang_code"
    ).unique(["word", "lang_code"])

    entry2vert = vert_df.select(
        "entry_id", "vert_id"
    )

    # NOTE: known outlier
    weak_edges = weak_edges.filter(
        pl.col("peer_word") != "Sino-Korean"
    )

    # fix peer ids
    edges_df = weak_edges.drop("peer_id", strict=False).join(
        wordlang2vert.rename({
            "vert_id": "peer_id",
        }),
        left_on=["peer_word", "peer_lang"],
        right_on=["word", "lang_code"],
        how="left"
    )

    # fix host ids
    edges_df = edges_df.rename({
        "host_id": "host_entry_id",
    }).join(
        entry2vert.rename({
            "vert_id": "host_id",
        }),
        left_on="host_entry_id",
        right_on="entry_id",
        how="left"
    ).drop("host_entry_id").with_columns(
        (pl.col("peer_word").str.starts_with("-")
         | pl.col("peer_word").str.ends_with("-")
        ).alias("affix")
    )

    

    edges_df.write_parquet("data/step4/edges_debug.parquet")
    edges_df = edges_df.drop(["peer_word", "peer_lang", "palt_word", "palt_lang"])
    edges_df.write_parquet("data/step4/edges.parquet")



if __name__ == "__main__":
    # make_vertices()
    make_edges()