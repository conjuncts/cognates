import polars as pl
from tqdm import tqdm
from etytreealg.decode.decode_templates import get_langcodes_and_words
from etytreealg.decode.decode_words import decode_word
from etytreealg.decode import langcodes as langcodes


def most_common_referenced_languages(df, src_langcode, sortme=True, hreadable=False, need_subset=False):
    lang_freqs = {}
    if need_subset:
        subset = df.filter(pl.col("lang_code") == src_langcode)
    else:
        subset = df
    for templates in tqdm(subset["templates_h"]):
        if not templates:
            continue
        for template in templates:
            langs, words = get_langcodes_and_words(template['name'], template['args'], src_langcode)
            for lang in langs:
                if lang not in lang_freqs:
                    lang_freqs[lang] = 0
                lang_freqs[lang] += 1
    if hreadable:
        _result = {}
        for k, v in lang_freqs.items():
            name = langcodes.langcode_to_name(k)
            if name:
                if name in _result:
                    _result[name] += v
                else:
                    _result[name] = v
            else:
                _result[k] = v
        lang_freqs = _result
    if sortme:
        lang_freqs = {k: v for k, v in sorted(lang_freqs.items(), key=lambda item: item[1], reverse=True)}

    return lang_freqs

def construct_edges_df(target_df):
    view = target_df[['lang', 'lang_code', 'word', 'templates_h', 'etymology_number']]

    edges = {
        'host_word': [],
        'host_lang': [],
        'host_ety': [],
        'parent_word': [],
        'parent_lang': [],
        'template_name': []
    }

    for j, (host_lang, host_langcode, host_word, templates, e_num) in enumerate(tqdm(view.iter_rows(), total=view.height)):

        for template in templates:
            # if template['name'] != 'suf':
            #     continue
            codes, words = get_langcodes_and_words(template['name'], template['args'], host_langcode)

            if len(codes) > 1 or len(codes) == 0:
                # for simplicity, skip for now
                continue
            langcode = codes[0]
            for word in words:
                decoded_word = decode_word(word, langcode=langcode)
                if not decoded_word.strip():
                    continue
                # if decoded_word not in all_word_set:
                    # print(f"Host: {host_word}#{host_lang}. {template['name']} | {decoded_word}#{langcode}")
                # edge = (host_word, host_langcode, decoded_word, langcode, template['name'])
                edges['host_word'].append(host_word)
                edges['host_lang'].append(host_langcode)
                edges['host_ety'].append(e_num)
                edges['parent_word'].append(decoded_word)
                edges['parent_lang'].append(langcode)
                edges['template_name'].append(template['name'])
        # if j > 1000:
        #     break
    edges_df = pl.DataFrame(edges)
    edges_df = edges_df.with_row_index("edge_id")
    # del edges
    return edges_df

def construct_adjacency_dfs(edges_df):
    """
    Construct the vertex df, and also the adjacency list, for the graph, given the edges_df.
    """
    # edges_df = edges_df.with_columns([
    #     pl.lit(-1, dtype=pl.Int64).alias("target_ety"),
    # ])

    vertex_df = (
        pl.concat([
            # edges_df[['host_word', 'host_lang', 'host_ety']]
            #   .rename({"host_word": "word", "host_lang": "lang", "host_ety": "ety_number"}),
            # edges_df[['parent_word', 'parent_lang', 'target_ety']]
            #   .rename({"parent_word": "word", "parent_lang": "lang", "target_ety": "ety_number"}),
            edges_df[['host_word', 'host_lang']]
                .rename({"host_word": "word", "host_lang": "lang"}),
            edges_df[['parent_word', 'parent_lang']]
                .rename({"parent_word": "word", "parent_lang": "lang"}),
        ]).unique().with_row_index("vertex_id")
    )

    extended_edges_df = (
        edges_df
        # .join(vertex_df, left_on=["host_word", "host_lang", "host_ety"], right_on=["word", "lang", "ety_number"])
        .join(vertex_df, left_on=["host_word", "host_lang"], right_on=["word", "lang"])
        .rename({"vertex_id": "host_id"})
        # .join(vertex_df, left_on=["parent_word", "parent_lang", "target_ety"], right_on=["word", "lang", "ety_number"])
        .join(vertex_df, left_on=["parent_word", "parent_lang"], right_on=["word", "lang"])
        .rename({"vertex_id": "parent_id"})
    )

    source_edges = (
        extended_edges_df
        .group_by("host_id")
        .agg(pl.col("edge_id").alias("ancestral_edge_ids")) # the host will provide ancestors
        
    )
    target_edges = (
        extended_edges_df
        .group_by("parent_id")
        .agg(pl.col("edge_id").alias("descendant_edge_ids")) # the parent will provide descendants
        
    )

    extended_vertex_df = (
        vertex_df
        .join(source_edges, left_on="vertex_id", right_on="host_id", how="left")
        .join(target_edges, left_on="vertex_id", right_on="parent_id", how="left")
    )

    return extended_vertex_df, extended_edges_df