import polars as pl
from tqdm import tqdm
from etytreealg.decode.decode_templates import get_langcodes_and_words
from etytreealg.decode.decode_words import decode_langcode, decode_word, decode_word_langcode
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

def construct_descendant_edges_df(target_df):
    # [{"depth": 1, "templates": [{"name": "desc", "args": {"1": "nb", "2": "abolisjonisme"}, "expansion": "Norwegian Bokm\u00e5l: abolisjonisme"}], "text": "Norwegian Bokm\u00e5l: abolisjonisme"}, {"depth": 1, "templates": [{"name": "desc", "args": {"1": "pl", "2": "abolicjonizm"}, "expansion": "Polish: abolicjonizm"}], "text": "Polish: abolicjonizm"}]
    # [{"depth": 2, "templates": [], "text": "Gallo-Italic:"}, {"depth": 3, "templates": [{"name": "desc", "args": {"1": "lij", "2": "messoia"}, "expansion": "Ligurian: messoia"}], "text": "Ligurian: messoia"}, {"depth": 3, "templates": [{"name": "desc", "args": {"1": "lmo", "2": "n\u00f6ra"}, "expansion": "Lombard: n\u00f6ra"}], "text": "Lombard: n\u00f6ra"}, {"depth": 3, "templates": [{"name": "desc", "args": {"1": "pms", "2": "messoira"}, "expansion": "Piedmontese: messoira"}], "text": "Piedmontese: messoira"}, {"depth": 3, "templates": [], "text": ""}, {"depth": 0, "templates": [], "text": "ablative feminine singular of mess\u014drius"}]
    view = target_df[['lang', 'lang_code', 'word', 'descendants_h']]
    edges = {
        'host_word': [],
        'host_lang': [],
        'host_ety': [],
        'other_word': [],
        'other_lang': [],
        'replaced_other_word': [],
        'replaced_other_lang': [],
        'template_name': []
    }

    unexpected_templates = {}
    for j, (host_lang, host_langcode, host_word, descendants) in enumerate(tqdm(view.iter_rows(), total=view.height)):

        for descendant in descendants:
            for template in descendant['templates']:
                if template['name'] in ['desc', 'descendants']:
                    langcode = template['args']['1']
                    words = []

                    for key, value in template['args'].items():
                        if key.isnumeric() and int(key) > 1:
                            words.append(value)
                else:
                    if template['name'] not in unexpected_templates:
                        unexpected_templates[template['name']] = 0
                    unexpected_templates[template['name']] += 1

                    codes, words = get_langcodes_and_words(template['name'], template['args'], host_langcode)

                    if len(codes) > 1 or len(codes) == 0:
                        # for simplicity, skip for now
                        continue
                    langcode = codes[0]
                
                
                
                
                for word in words:
                    decoded_word, decoded_langcode = decode_word_langcode(word, langcode)
                    if not decoded_word.strip():
                        continue
                    edges['host_word'].append(host_word)
                    edges['host_lang'].append(host_langcode)
                    edges['host_ety'].append(descendant['depth'])
                    edges['other_word'].append(decoded_word)
                    edges['other_lang'].append(decoded_langcode)
                    edges['replaced_other_lang'].append(langcode if langcode != decoded_langcode else None)
                    edges['replaced_other_word'].append(word if word != decoded_word else None)
                    edges['template_name'].append(template['name'])
    print("Unexpected templates:")
    print(unexpected_templates)

    edges_df = pl.DataFrame(edges)

    # drop duplicates in all columns
    edges_df = edges_df.unique(maintain_order=True)
    edges_df = edges_df.with_row_index("edge_id")
    # del edges
    return edges_df


def construct_edges_df(target_df):
    view = target_df[['lang', 'lang_code', 'word', 'templates_h', 'etymology_number']]

    edges = {
        'host_word': [],
        'host_lang': [],
        'host_ety': [],
        'other_word': [],
        'other_lang': [],
        'replaced_other_lang': [],
        'replaced_other_word': [],
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
                
                decoded_word, decoded_langcode = decode_word_langcode(word, langcode)
                if not decoded_word.strip():
                    continue
                # if decoded_word not in all_word_set:
                    # print(f"Host: {host_word}#{host_lang}. {template['name']} | {decoded_word}#{langcode}")
                # edge = (host_word, host_langcode, decoded_word, langcode, template['name'])
                edges['host_word'].append(host_word)
                edges['host_lang'].append(host_langcode)
                edges['host_ety'].append(e_num)
                edges['other_word'].append(decoded_word)
                edges['other_lang'].append(decoded_langcode)
                edges['replaced_other_lang'].append(langcode if langcode != decoded_langcode else None)
                edges['replaced_other_word'].append(word if word != decoded_word else None)
                edges['template_name'].append(template['name'])
        # if j > 1000:
        #     break
    edges_df = pl.DataFrame(edges)

    # drop duplicates in all columns
    edges_df = edges_df.unique(maintain_order=True)
    edges_df = edges_df.with_row_index("edge_id")
    # del edges
    return edges_df

def construct_adjacency_dfs(weak_edges_df, weak_desc_edges_df=None):
    """
    Construct the vertex df, and also the adjacency list, for the graph, given the edges_df.
    """
    # edges_df = edges_df.with_columns([
    #     pl.lit(-1, dtype=pl.Int64).alias("target_ety"),
    # ])

    to_concat = [
        # edges_df[['host_word', 'host_lang', 'host_ety']]
        #   .rename({"host_word": "word", "host_lang": "lang", "host_ety": "ety_number"}),
        # edges_df[['parent_word', 'parent_lang', 'target_ety']]
        #   .rename({"parent_word": "word", "parent_lang": "lang", "target_ety": "ety_number"}),
        weak_edges_df[['host_word', 'host_lang']]
            .rename({"host_word": "word", "host_lang": "lang"}),
        weak_edges_df[['parent_word', 'parent_lang']]
            .rename({"parent_word": "word", "parent_lang": "lang"}),
    ]
    if weak_desc_edges_df is not None:
        to_concat.extend([
            weak_desc_edges_df[['host_word', 'host_lang']]
                .rename({"host_word": "word", "host_lang": "lang"}),
            weak_desc_edges_df[['descendant_word', 'descendant_lang']]
                .rename({"descendant_word": "word", "descendant_lang": "lang"}),
        ])
    vertex_df = (
        pl.concat(to_concat).unique(maintain_order=True).with_row_index("vertex_id")
    )

    extended_edges_df = (
        weak_edges_df
        # .join(vertex_df, left_on=["host_word", "host_lang", "host_ety"], right_on=["word", "lang", "ety_number"])
        .join(vertex_df, left_on=["host_word", "host_lang"], right_on=["word", "lang"])
        .rename({"vertex_id": "host_id"})
        # .join(vertex_df, left_on=["parent_word", "parent_lang", "target_ety"], right_on=["word", "lang", "ety_number"])
        .join(vertex_df, left_on=["parent_word", "parent_lang"], right_on=["word", "lang"])
        .rename({"vertex_id": "parent_id"})
        .with_columns([
            pl.lit(False).alias("desc_relation")
        ])
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

    # desc edges time
    
    if weak_desc_edges_df is not None:
        extended_desc_edges_df = (
            weak_desc_edges_df
            .join(vertex_df, left_on=["host_word", "host_lang"], right_on=["word", "lang"])
            .rename({"vertex_id": "host_id"})
            .join(vertex_df, left_on=["descendant_word", "descendant_lang"], right_on=["word", "lang"])
            .rename({"vertex_id": "descendant_id"}).with_columns([
                pl.lit(True).alias("desc_relation")
            ])
        )

        source_desc_edges = (
            extended_desc_edges_df
            .group_by("host_id")
            .agg(pl.col("edge_id").alias("desc_descendant_edge_ids")) # the host will provide descendants
        )
        target_desc_edges = (
            extended_desc_edges_df
            .group_by("descendant_id")
            .agg(pl.col("edge_id").alias("desc_ancestral_edge_ids")) # the descendant will provide ancestors
        )
        extended_vertex_df = (
            extended_vertex_df
            .join(source_desc_edges, left_on="vertex_id", right_on="host_id", how="left")
            .join(target_desc_edges, left_on="vertex_id", right_on="descendant_id", how="left")
        )
        # merge the two edge types
        extended_vertex_df = extended_vertex_df.with_columns(
            pl.concat_list([
                pl.col("descendant_edge_ids").fill_null(pl.lit([])),
                pl.col("desc_descendant_edge_ids").fill_null(pl.lit([]))
            ]).replace([], None).alias("descendant_edge_ids"),
            pl.concat_list([
                pl.col("ancestral_edge_ids").fill_null(pl.lit([])),
                pl.col("desc_ancestral_edge_ids").fill_null(pl.lit([]))
            ]).replace([], None).alias("ancestral_edge_ids")
        )

    if weak_desc_edges_df is not None:
        return extended_vertex_df, extended_edges_df, extended_desc_edges_df

    return extended_vertex_df, extended_edges_df