import polars as pl
from tqdm import tqdm
from etytreealg.decode.decode_templates import get_langcodes_and_words
from etytreealg.decode.decode_words import decode_langcode, decode_word, decode_word_langcode
from etytreealg.decode import langcodes as langcodes


def construct_descendant_edges_flat_df(entry_df: pl.DataFrame, descendants_df: pl.DataFrame):
    """
    Flat version of construct_descendant_edges_df.
    Works with flattened descendants data where each row contains entry_id, item_number, key, value.
    
    Args:
        entry_df: DataFrame with entry_id, lang_code, word columns
        descendants_df: Flattened descendants DataFrame with entry_id, item_number, key, value columns
    """
    
    # Join with entry_df to get host_lang
    with_lang = descendants_df.lazy().join(
        entry_df.lazy().select('entry_id', 'lang_code'),
        on='entry_id',
        how='left'
    )
    
    # Extract depth and template information
    # Keys like: 'depth', 'templates[0].name', 'templates[0].args.1', 'templates[0].args.2', etc.
    
    # Get depth values for each item
    
    # Get template data - need to parse templates[X].name and templates[X].args.*
    view = with_lang.group_by('entry_id', 'lang_code', 'item_number').agg([
        'key',
        'value'
    ])
    # view = view.head(10)
    view = view.collect()
    
    edges = {
        'host_id': [],
        'peer_word': [],
        'peer_lang': [],
        'palt_word': [],
        'palt_lang': [],
        'template_name': [],
    }
    
    unexpected_templates = {}
    
    for host_id, _, host_langcode, keys, values in tqdm(view.iter_rows(), total=view.height):

        # need more robust parsing
        args = {}
        for k, v in zip(keys, values):
            if v is None:
                continue # ???
            if k.startswith('templates['):
                template_number, rest = k.split('].', 1)
                rest = rest.removeprefix("args.")
                args[rest] = v
            else:
                args[k] = v
        if 'name' not in args:
            # Apparently this is possible
            continue
        # assert 'name' in args, f"Template missing name: {args}"
        template_name = args.pop('name')
        if template_name in ['desc', 'descendants']:
            langcode = args.get('1')
            if not langcode:
                continue
            words = [v for k, v in args.items() if k.isnumeric() and int(k) > 1]
        else:
            if template_name not in unexpected_templates:
                unexpected_templates[template_name] = 0
            unexpected_templates[template_name] += 1
            
            codes, words = get_langcodes_and_words(template_name, args, host_langcode)
            
            if len(codes) > 1 or len(codes) == 0:
                continue
            langcode = codes[0]
        
        for word in words:
            decoded_word, decoded_langcode = decode_word_langcode(word, langcode)
            if not decoded_word.strip():
                continue
            
            edges['host_id'].append(host_id)
            edges['peer_word'].append(decoded_word)
            edges['peer_lang'].append(decoded_langcode)
            edges['palt_word'].append(word if word != decoded_word else None)
            edges['palt_lang'].append(langcode if langcode != decoded_langcode else None)
            edges['template_name'].append(template_name)
    
    if unexpected_templates:
        print("Unexpected templates in descendants:")
        print(unexpected_templates)
    
    edges_df = pl.DataFrame(edges).lazy()
    
    # Drop duplicates and add metadata
    edges_df = edges_df.with_columns([
        pl.lit('desc').alias("edge_type")
    ])
    
    return edges_df


def construct_edges_flat_df(entry_df: pl.DataFrame, templates_df: pl.DataFrame):
    """
    Modification of construct_edges_flat_df
    """

    # need to obtain host_lang
    with_lang = templates_df.lazy().join(
        entry_df.lazy().select('entry_id', 'lang_code'),
        on='entry_id',
        how='left'
    )

    view = with_lang.group_by('entry_id', 'lang_code', 'template_number', 'template_name').agg([
        'key',
        'value'
    ])
    # view = view.head(10)
    view = view.collect()
    # Note that within groups, the order is always preserved.

    pass
    edges = {
        'host_id': [],
        'peer_word': [], # formally "other"
        'peer_lang': [],
        'palt_word': [],
        'palt_lang': [],
        'template_name': []
    }
    for host_id, host_langcode, _, template_name, keys, values in tqdm(view.iter_rows(), total=view.height):

        args = {k.removeprefix("args."): v for k, v in zip(keys, values) if v is not None}
        codes, words = get_langcodes_and_words(template_name, args, host_langcode)

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
            edges['host_id'].append(host_id)
            edges['peer_word'].append(decoded_word)
            edges['peer_lang'].append(decoded_langcode)
            edges['palt_word'].append(word if word != decoded_word else None)
            edges['palt_lang'].append(langcode if langcode != decoded_langcode else None)
            edges['template_name'].append(template_name)
        # if j > 1000:
        #     break
    edges_df = pl.DataFrame(edges)
    edges_df = edges_df.lazy()

    # drop duplicates in all columns
    edges_df = edges_df.with_columns([
        pl.lit('normal').alias("edge_type")
    ])
    # del edges
    return edges_df

def construct_related_edges_flat_df(related_df: pl.DataFrame):
    """
    Note: related words are often NOT direct etymological ancestors/descendants 
    (more like cousins/cognates). Not needed for graph construction.
    See step3/related_flat.parquet
    """


def construct_forms_of_flat_df(entry_df: pl.DataFrame):
    """
    Flat version of construct_forms_of_df.
    Works with forms_of data.
    
    Args:
        entry_df: DataFrame with entry_id, lang_code, word columns
    """
    view = entry_df.select('entry_id', 'lang_code', 'forms_of').filter(
        pl.col('forms_of').is_not_null()
    ).explode("forms_of").select(
        "entry_id", "lang_code", "forms_of"
    )
    # view = view.head(10)

    edges = {
        'host_id': [],
        'peer_word': [],
        'peer_lang': [],
        'palt_word': [],
        'palt_lang': [],
        'template_name': []
    }

    for host_id, host_langcode, related_word in tqdm(view.iter_rows(), total=view.height):

        langcode = host_langcode
        decoded_word, decoded_langcode = decode_word_langcode(related_word, langcode)
        if not decoded_word.strip():
            continue
        edges['host_id'].append(host_id)
        edges['peer_word'].append(decoded_word)
        edges['peer_lang'].append(decoded_langcode)
        edges['palt_word'].append(related_word if related_word != decoded_word else None)
        edges['palt_lang'].append(langcode if langcode != decoded_langcode else None)
        edges['template_name'].append('form of')

    edges_df = pl.DataFrame(edges).lazy()

    edges_df = edges_df.with_columns([
        pl.lit("lemma").alias("edge_type")
    ])
    
    # edges_df = edges_df.collect()
    return edges_df
