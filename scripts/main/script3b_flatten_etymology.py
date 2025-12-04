"""
Attempt to flatten `data/step2/ety_expanded.parquet`, making it easier to work with
"""
import json
import polars as pl
import os

from tqdm import tqdm

def flat_iter_dict(d, parent_key='', sep='.'):
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            yield from flat_iter_dict(v, new_key, sep=sep)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    yield from flat_iter_dict(item, f"{new_key}[{i}]", sep=sep)
                else:
                    yield f"{new_key}[{i}]", item
        else:
            yield new_key, v

def flatten_json_field(df, field_name, output_filename):
    """
    Flatten a JSON field from a DataFrame and save to parquet.
    
    Args:
        df: polars DataFrame containing the field to flatten
        field_name: name of the column containing JSON data
        output_filename: filename to save the flattened data
    """
    collector = []
    series = df[field_name]
    
    for entry_id, json_obj in tqdm(enumerate(series), total=len(series), desc=f"Flattening {field_name}"):
        obj = json.loads(json_obj) if json_obj else []
        for i, item in enumerate(obj):
            for k, v in flat_iter_dict(item):
                collector.append((entry_id, i, k, str(v) or None))
    
    flattened_df = pl.DataFrame(collector, schema=['entry_id', 'item_number', 'key', 'value'], orient='row')
    del collector  # Free memory
    flattened_df.write_parquet(f'data/step3/{output_filename}')
    print(f"Saved flattened {field_name} to data/step3/{output_filename}")
    del flattened_df  # Free memory after saving
    return flattened_df



def flatten_template(df):
    """
    Flatten a template field from a DataFrame and save to parquet.
    
    Args:
        df: polars DataFrame containing the field to flatten
        field_name: name of the column containing JSON data
        output_filename: filename to save the flattened data
    """
    field_name = 'templates'
    output_filename = 'templates_flat.parquet'

    collector = []
    series = df[field_name]
    
    for entry_id, json_obj in tqdm(enumerate(series), total=len(series), desc=f"Flattening {field_name}"):
        obj = json.loads(json_obj) if json_obj else []
        for i, item in enumerate(obj):
            name = item.get('name', '')
            item.pop('name', None)  # Remove name from item to avoid duplication

            recorded = False
            for k, v in flat_iter_dict(item):
                recorded = True
                collector.append((entry_id, i, name, k, str(v) or None))
            if not recorded:
                collector.append((entry_id, i, name, None, None))

    flattened_df = pl.DataFrame(collector, schema=['entry_id', 'template_number', 'template_name', 'key', 'value'], orient='row')
    del collector  # Free memory
    flattened_df.write_parquet(f'data/step3/{output_filename}')
    print(f"Saved flattened {field_name} to data/step3/{output_filename}")
    del flattened_df  # Free memory after saving

def script3b_flatten_df():
    os.makedirs('data/step3', exist_ok=True)

    df_dest = 'data/step2/ety_expanded.parquet'

    # note that Object datatype cannot be written to parquet/arrow
    # df = df.with_columns([
    #     pl.col('templates').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('templates_h'),
    #     pl.col('related').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('related_h'),
    #     pl.col('descendants').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('descendants_h'),
    # ])

    df = pl.read_parquet(df_dest)
    df = df.with_row_index('entry_id')

    # Flatten each JSON field
    flatten_template(df)
    flatten_json_field(df, 'related', 'related_flat.parquet')
    flatten_json_field(df, 'descendants', 'descendants_flat.parquet')

    # Save the main dataframe without the JSON fields
    df.select(
        pl.selectors.exclude('templates', 'related', 'descendants')
    ).write_parquet('data/step3/ety_expanded_flat.parquet')

if __name__ == '__main__':
    script3b_flatten_df()
    print("Flattening completed and saved to 'data/step3/'")