import polars as pl
from supabase import create_client
import os
from typing import List, Dict, Any
import time
from tqdm import tqdm


env_dict = {}
with open('.env', 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=')
            env_dict[key] = value
    
# Supabase configuration
SUPABASE_URL = env_dict['SUPABASE_URL']
SUPABASE_KEY = env_dict['SERVICE_KEY']

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Authenticate and get the JWT
# auth_response = supabase.auth.sign_in_with_password({"email": "galen.wei@vanderbilt.com", "password": env_dict['ADMIN_PASS']})
# access_token = auth_response.session.access_token

# Use the access token in subsequent requests
# supabase.auth.set_auth(access_token)

def create_tables():
    """
    Create tables using Supabase's database functions.
    Note: You'll need to run this SQL in the Supabase SQL editor first.
    """
    SQL = """
    -- Enable the pgvector extension
    create extension if not exists vector;

    -- Create vertices table
    create table if not exists vertices (
        vertex_id integer primary key,
        word text not null,
        lang text not null,

        -- UNUSED
        -- ancestral_edge_ids integer[],
        -- descendant_edge_ids integer[]
    );

    -- Create edges table
    create table if not exists edges (
        edge_id integer primary key,
        -- host_word text not null,
        -- host_lang text not null,
        host_ety int2,
        -- parent_word text not null,
        -- parent_lang text not null,
        template_name text not null,
        host_id integer not null references vertices(vertex_id),
        parent_id integer not null references vertices(vertex_id)
    );

    -- Create indexes
    create index if not exists idx_vertices_word_lang on vertices(word, lang);
    create index if not exists idx_edges_host on edges(host_id);
    create index if not exists idx_edges_parent on edges(parent_id);
    create index if not exists idx_edges_template on edges(template_name);

    -- Create GiST index for array operations
    create index if not exists idx_vertices_ancestral on vertices using gin (ancestral_edge_ids);
    create index if not exists idx_vertices_descendant on vertices using gin (descendant_edge_ids);
    """
    print("Note: Run the above SQL in Supabase SQL editor first")
    return SQL

def batch_insert_vertices(vertex_df: pl.DataFrame, batch_size: int = 500):
    """Insert vertices in batches with progress bar"""
    total_rows = len(vertex_df)
    
    for start_idx in tqdm(range(0, total_rows, batch_size), desc="Inserting vertices"):
        batch_df = vertex_df.slice(start_idx, batch_size)
        
        # Convert to list of dictionaries
        vertices_data = batch_df.select([
            'vertex_id',
            'word',
            'lang',
            'ancestral_edge_ids',
            'descendant_edge_ids'
        ]).to_dicts()
        
        # Replace None with empty arrays for PostgreSQL
        for vertex in vertices_data:
            if vertex['ancestral_edge_ids'] is None:
                vertex['ancestral_edge_ids'] = []
            if vertex['descendant_edge_ids'] is None:
                vertex['descendant_edge_ids'] = []
        
        try:
            supabase.table('vertices').insert(vertices_data).execute()
            
        except Exception as e:
            print(f"Error inserting batch starting at index {start_idx}: {e}")
            continue
        
        # Small delay to avoid rate limits
        time.sleep(0.1)

def batch_insert_edges(edges_df: pl.DataFrame, batch_size: int = 500):
    """Insert edges in batches with progress bar"""
    total_rows = len(edges_df)
    
    for start_idx in tqdm(range(0, total_rows, batch_size), desc="Inserting edges"):
        if start_idx // batch_size < 1358:
            continue
        batch_df = edges_df.slice(start_idx, batch_size)
        
        # Convert to list of dictionaries
        edges_data = batch_df.select([
            'edge_id',
            # 'host_word',
            # 'host_lang',
            'host_ety',
            # 'parent_word',
            # 'parent_lang',
            'template_name',
            'host_id',
            'parent_id'
        ]).to_dicts()
        
        try:
            supabase.table('edges').insert(edges_data).execute()
            
        except Exception as e:
            print(f"Error inserting batch starting at index {start_idx}: {e}")
            continue
        
        # Small delay to avoid rate limits
        time.sleep(0.1)

def verify_data():
    """Verify the data was inserted correctly"""
    try:
        # Check vertex count
        vertex_count = supabase.table('vertices').select('count', count='exact').execute()
        print(f"Total vertices: {vertex_count}")
        
        # Check edge count
        edge_count = supabase.table('edges').select('count', count='exact').execute()
        print(f"Total edges: {edge_count}")
        
        # Sample query to verify relationships
        sample = supabase.table('edges')\
            .select('edge_id,host_word,parent_word,template_name')\
            .limit(5)\
            .execute()
        print("\nSample edges:")
        print(sample)
        
    except Exception as e:
        print(f"Error verifying data: {e}")


def express_vertex_id_using_old_parquet(old_vertex_csv: pl.DataFrame, new_vertex_csv: pl.DataFrame, 
                                        old_edge_csv: pl.DataFrame, new_edge_csv: pl.DataFrame) -> pl.DataFrame:
    """
    Given new_vertex_df (which has vertex_id, word, lang) look for the matching word in old_vertex_df
    and look for the vertex_id and put old_vertex_id as a column into new_vertex_df
    """

    old_vertex_csv = old_vertex_csv.select([
        'vertex_id',
        'word',
        'lang'
    ]).rename({'vertex_id': 'old_vertex_id'})

    old_largest_index = old_vertex_csv.select(pl.max('old_vertex_id')).item()
    old_largest_edge_index = old_edge_csv.select(pl.max('edge_id')).item()

    new_vertex_csv = new_vertex_csv.join(old_vertex_csv, on=['word', 'lang'], how='left')

    # assign nulls to the new vertex_ids

    new_vertex_csv_found = new_vertex_csv.filter(pl.col('old_vertex_id').is_not_null())
    new_vertex_csv_not_found = new_vertex_csv.filter(pl.col('old_vertex_id').is_null())

    new_vertex_csv_not_found.drop_in_place('old_vertex_id')
    new_vertex_csv_not_found = new_vertex_csv_not_found \
        .with_row_index('old_vertex_id', offset=old_largest_index + 1).select([
            'vertex_id',
            'word',
            'lang',
            'old_vertex_id',
        ]).cast({"old_vertex_id": pl.Int64})

    new_vertex_csv = pl.concat([
        new_vertex_csv_found,
        new_vertex_csv_not_found
    ])

    reindex_map = new_vertex_csv.select(['vertex_id', 'old_vertex_id'])

    # every vertex_id in edges should be mapped to the new vertex_id, and they should be unique
    # and they should have the same height
    assert_reindex_map = reindex_map.unique(['vertex_id']).unique('old_vertex_id')

    assert assert_reindex_map.height == reindex_map.height == new_vertex_csv.height, \
            f"Reindex map is not unique: {assert_reindex_map.height()} != {reindex_map.height()} != {new_vertex_csv.height()}"
    # map host_id and parent_id in edges, and map them 

    new_edge_csv = new_edge_csv.join(reindex_map, left_on='host_id', right_on='vertex_id', how='left').rename({
        'old_vertex_id': 'new_host_id'
    }).join(reindex_map, left_on='parent_id', right_on='vertex_id', how='left').rename({
        'old_vertex_id': 'new_parent_id'
    })
    

    # now get the strictly novel components
    novel_vertex_csv = new_vertex_csv.filter(
        pl.col('old_vertex_id') > old_largest_index
    ).drop('vertex_id').rename({
        'old_vertex_id': 'vertex_id'
    }).select(['vertex_id', 'word', 'lang'])


    novel_edge_csv = new_edge_csv.filter(
        (pl.col('new_host_id') > old_largest_index) | (pl.col('new_parent_id') > old_largest_index)
    ).drop('host_id', 'parent_id', 'edge_id').rename({
        'new_host_id': 'host_id',
        'new_parent_id': 'parent_id'
    }).with_row_index('edge_id', offset=old_largest_edge_index + 1).cast({'edge_id': pl.Int64}).select(['edge_id', 'host_id', 'parent_id'])

    return novel_vertex_csv, novel_edge_csv
    


def script_parquet_to_csv(langname='spanish'):

    print("Reading Parquet files...")
    vertex_df = pl.read_parquet(f'data/parquet/{langname}_vertices.parquet')
    edges_df = pl.read_parquet(f'data/parquet/{langname}_edges.parquet')
    desc_edges_df = pl.read_parquet(f'data/parquet/{langname}_desc_edges.parquet')


    # so that we need to serve fewer languages, prune edges if they are leaf nodes (modern languages)
    # but aren't of the desired language
    # we want to keep these langcodes:
    # es, pt, fr, it, en, la, osp, fro, grc, ine-pro, itc-pro, de, nl, 
    # sv, no, da, ro, 
    ok_modern_langs = ['es', 'pt', 'fr', 'it', 'en', 'la', 'osp', 'fro', 'grc', 'ine-pro', 'itc-pro', 'de', 'nl', 'sv', 'no', 'da', 'ro', 'el', 'ar', 'af']
    
    pruned_df = vertex_df.filter([
        pl.col('lang').is_in(ok_modern_langs)
        | (pl.col('descendant_edge_ids').list.len() > 0)
        | (pl.col('desc_descendant_edge_ids').list.len() > 0)
    ])
    ok_vertices = set(pruned_df['vertex_id'])
    # _dist = pruned_df['lang'].value_counts(sort=True)

    # controversially removes: catalan, galician, scots, 
    # lots from middle/old english, afrikaans?, turkish, icelandic
    
    # then, we only need to modify edges_df. vertices_df can stay untouched
    # edges:
    edges_export_df = edges_df.filter([
        (pl.col('template_name') != 'cog') 
        & (pl.col('template_name') != 'cognate')
        & (pl.col('host_id').is_in(ok_vertices))
        & (pl.col('parent_id').is_in(ok_vertices))

    ]).select([
        # 'edge_id',
        'host_id',
        'parent_id'
    ]).unique(['host_id', 'parent_id'], maintain_order=True) 


    desc_edges_export_df = desc_edges_df.filter([
        (pl.col('host_id').is_in(ok_vertices))
        & (pl.col('descendant_id').is_in(ok_vertices))
    ]).select([
        'descendant_id',
        'host_id',
    ]).unique(['host_id', 'descendant_id'], maintain_order=True).rename({
        'descendant_id': 'host_id',
        'host_id': 'parent_id'
    })

    edges_export_df = pl.concat([
        edges_export_df, 
        desc_edges_export_df
    ]).unique(['host_id', 'parent_id'], maintain_order=True).with_row_index('edge_id')

    # remove self edges
    edges_export_df = edges_export_df.filter(pl.col('host_id') != pl.col('parent_id'))
    print(edges_export_df)

    vertex_export_df = vertex_df.select([
        'vertex_id',
        'word',
        'lang'
    ]).unique(['word', 'lang']).sort('vertex_id')

    # perform a reindex, based on the old vertex_df


    edges_export_df.write_csv(f'data/csv/{langname}_edges.csv')
    vertex_export_df.write_csv(f'data/csv/{langname}_vertices.csv')
    print(vertex_export_df)

    # vertex_df.write_ipc('data/arrow/spanish_vertices.ipc')
    # edges_df.write_ipc('data/arrow/spanish_edges.ipc')



def main():
    # Read Parquet files
    # script_parquet_to_csv()
    script_parquet_to_csv('spanish')

    vertex_df = pl.read_csv('data/csv/german_vertices.csv')
    edges_df = pl.read_csv('data/csv/german_edges.csv')
    # old_vertex_df = pl.read_csv('data/csv/spanish_vertices.csv')
    # old_edges_df = pl.read_csv('data/csv/spanish_edges.csv')
    old_vertex_df = pl.read_csv('data/csv/latest_vertices.csv')
    old_edges_df = pl.read_csv('data/csv/latest_edges.csv')

    novel_vertex_df, novel_edge_df = express_vertex_id_using_old_parquet(old_vertex_df, vertex_df, old_edges_df, edges_df)

    novel_vertex_df.write_csv('data/csv/novel_vertices.csv')
    novel_edge_df.write_csv('data/csv/novel_edges.csv')

    latest_vertex_df = pl.concat([
        old_vertex_df,
        novel_vertex_df
    ]).sort('vertex_id')

    latest_edge_df = pl.concat([
        old_edges_df,
        novel_edge_df
    ]).sort('edge_id')

    latest_vertex_df.write_csv('data/csv/latest_vertices.csv')
    latest_edge_df.write_csv('data/csv/latest_edges.csv')
    exit(0)
    
    print("\nInserting data...")
    # stopped at 1358/4098
    try:
        # Insert vertices first (required for foreign key constraints)
        # batch_insert_vertices(vertex_df)
        
        # Insert edges
        batch_insert_edges(edges_df)
        
        # Verify the data
        print("\nVerifying data...")
        verify_data()
        
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    main()