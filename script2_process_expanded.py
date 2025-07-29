"""
Expand the https://github.com/tatuylonen/wiktextract/ dump.
raw-wiktextract-data.json.gz
"""

import gzip
import json

import os
import glob
from tqdm import tqdm
import json
import polars as pl

import pickle as pkl

from etytreealg.decode.pl_infer_schema import convert_schema_to_polars, convert_to_polars_type, generate_polars_schema

def read_jsongz(filepath):
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            yield json.loads(line)



def process_record(data: dict) -> dict:
    """Process a single record into the desired format."""
    ety = data.get("etymology_text", "")
    templates = data.get("etymology_templates", [])
    word = data.get("word", "")
    lang = data.get("lang", "")
    lang_code = data.get("lang_code", "")
    etymology_number = data.get("etymology_number", 0)
    # subpart = data.get("subpart", 0)


    related = data.get("related", [])
    descendants = data.get("descendants", [])

    forms_of = {
        form["word"]
        for sense in data.get("senses", [])
        for form in sense.get("form_of", [])
    }
    # beside from "word", known additional keys: "extra"
    # for links in sense.get("links", []):
    #     for link in links:
    #         if '#' in link:
    #             # most useful link has a word + language code
    #             links_builder.add(link)
    to_push = {
        "word": word,
        "lang": lang,
        "lang_code": lang_code,
        "ety": ety if ety else None,
        "templates": json.dumps(templates) if templates else None,
        "etymology_number": etymology_number,
        "num_templates": len(templates),
        "related": json.dumps(related) if related else None,
        "descendants": json.dumps(descendants) if descendants else None,
        "forms_of": list(forms_of) if forms_of else None,
        # "links": list(links_builder),
    }
    # for k, v in to_push.items():
        # if v == 282:
        #     # debug
        #     print("WARNING: bad value", word)
        #     print(to_push)
        #     # print(k, v)

    return to_push

def script_to_df_parquet(filepath, chunk_size = 1000000, max_chunks=None):

    # count tokens in ./sorted
    
    collected = []

    so = {
        "word": pl.Utf8,
        "lang": pl.Utf8,
        "lang_code": pl.Utf8,
        "ety": pl.Utf8,
        "templates": pl.Utf8,
        "etymology_number": pl.UInt8,
        "num_templates": pl.UInt32,
        "related": pl.Utf8,
        "descendants": pl.Utf8,
        "forms_of": pl.List(pl.Utf8),
    }

    def save_checkpoint(split):
        nonlocal collected
        df = pl.DataFrame(collected, schema_overrides=so)
        df.write_parquet(f'data/step2/fragments/ety_expanded_{split}.parquet')
        collected = []

    split = 0
    for j, data in enumerate(tqdm(read_jsongz(filepath), total=9633555)):
        split = j // chunk_size

        if max_chunks is not None and split >= max_chunks:
            break
        
        to_push = process_record(data)

        collected.append(to_push)
        
        # chunks of 1 million, to ease up the RAM usage
        if j % chunk_size == chunk_size - 1:
            split = j // chunk_size

            save_checkpoint(split)
    if collected:
        save_checkpoint(split)
    
    df = script_condense_parquets()
    return df

def script_condense_parquets():
    dfs = []
    for filename in glob.glob(f'data/step2/fragments/ety_expanded_*.parquet'):
        df = pl.read_parquet(filename)
        dfs.append(df)
    df = pl.concat(dfs)
    df.write_parquet('data/step2/ety_expanded.parquet')
    return df

        
def script_generate_schema(col_name: str):
    """
    The schema are too complicated to be of use. Instead, we will continue to store the data as JSON strings.
    """
    # related
    # descendants
    sample_jsons = []
    for filename in glob.glob('data/step2/*.parquet'):
        df = pl.read_parquet(filename)
        jsons = df[col_name].to_list()
        sample_jsons.extend(jsons)
    sample_jsons = [j for j in sample_jsons if j]
    sample_jsons = [json.loads(j) for j in sample_jsons]
    
    # Generate schema
    schema = generate_polars_schema(sample_jsons)
    
    # Convert schema to Polars types
    
    
    return schema

if __name__ == '__main__':

    # script_condense_parquets()
    # exit(0)
    os.makedirs('data/step2/fragments', exist_ok=True)
    df_dest = 'data/step2/ety_expanded.parquet'
    if not os.path.exists(df_dest):
        script_to_df_parquet('data/raw/raw-wiktextract-data.json.gz') # , max_chunks=10)
    else:
        print("Data already exists. Loading.")
        df = pl.read_parquet(df_dest)
    
    print(df.shape)
    # Useful rows are where one of these are true:
    # num_templates OR related OR descendants OR forms_of
    useful_df = df.filter(
        (df['ety'].is_not_null()) |
        (df['related'].is_not_null()) |
        (df['descendants'].is_not_null()) | 
        (df['forms_of'].is_not_null())
    )
    print(useful_df.shape)
    # from 9633555 to 7578831

    
    # luckily, many of these do not need to be processed. we only need to process 
    # those with semantic information: where
    # num_templates >= 2 OR related OR descendants
    to_process_df = df.filter(
        (df['num_templates'] >= 2) |
        (df['related'].is_not_null()) |
        (df['descendants'].is_not_null())
    )
    print(to_process_df.shape)
    # from 9633555 to 1332932

    critical_df = df.filter(
        (df['num_templates'] >= 5)
    )
    print(critical_df.shape)
    # just 208140 

    etymological_df = df.filter(
        (df['num_templates'] >= 2)
    )
    print(etymological_df.shape)
    # 916730

    # s = script_generate_schema()
    if not os.path.exists('data/step2/templates_schema.json'):
        templates_schema = script_generate_schema('templates')
        related_schema = script_generate_schema('related')
        descendants_schema = script_generate_schema('descendants')
        # print(templates_schema)
        # print(related_schema)
        # print(descendants_schema)

        with open('data/step2/templates_schema.json', 'w') as f:
            json.dump(templates_schema, f)
        with open('data/step2/related_schema.json', 'w') as f:
            json.dump(related_schema, f)
        with open('data/step2/descendants_schema.json', 'w') as f:
            json.dump(descendants_schema, f)
    else:
        with open('data/step2/templates_schema.json', 'r') as f:
            templates_schema = json.load(f)
        with open('data/step2/related_schema.json', 'r') as f:
            related_schema = json.load(f)
        with open('data/step2/descendants_schema.json', 'r') as f:
            descendants_schema = json.load(f)
    
    # doesn't work
    # pl_templates_schema = convert_schema_to_polars(templates_schema)
    # pl_related_schema = convert_schema_to_polars(related_schema)
    # pl_descendants_schema = convert_schema_to_polars(descendants_schema)

    # # apply schema to the data
    # df = df.with_columns([
    #     pl.col('templates').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl_templates_schema).alias('templates_h'),
    #     pl.col('related').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl_related_schema).alias('related_h'),
    #     pl.col('descendants').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl_descendants_schema).alias('descendants_h'),
    # ])

    # # drop the original columns
    # df = df.drop_in_place(['templates', 'related', 'descendants'])
    # df.write_parquet('data/parquet/ety_hydrated.parquet')
    # print(s)
    pass