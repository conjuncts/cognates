import polars as pl
from collections import defaultdict


class UnionFind:
    """Union-Find data structure for finding connected components."""
    
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    
    def find(self, x):
        """Find root of x with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x, y):
        """Union two sets by rank."""
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return
        
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
    
    def get_components(self):
        """Get mapping from node to component ID."""
        # Find all unique roots
        roots = {}
        component_id = 0
        result = {}
        
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in roots:
                roots[root] = component_id
                component_id += 1
            result[i] = roots[root]
        
        return result


def find_connected_components(vert_df, edge_df):
    """
    Assign a connected component ID to each vertex.
    
    Args:
        vert_df: DataFrame with 'vert_id' column
        edge_df: DataFrame with 'peer_id' and 'host_id' columns (edges)
    
    Returns:
        DataFrame with 'vert_id' and 'conn_id' columns
    """
    # Get number of vertices
    max_vert_id = vert_df["vert_id"].max()
    n_vertices = max_vert_id + 1
    
    print(f"Total vertices: {n_vertices}")
    print(f"Total edges: {len(edge_df)}")
    
    # Initialize Union-Find
    uf = UnionFind(n_vertices)
    
    # Process all edges - treat graph as undirected for connected components
    edges = edge_df.select(["peer_id", "host_id"]).unique()
    
    print("Building connected components...")
    for peer_id, host_id in edges.iter_rows():
        uf.union(peer_id, host_id)
    
    # Get component assignments
    print("Assigning component IDs...")
    component_map = uf.get_components()
    
    # Get unique vertex IDs from the original dataframe
    unique_verts = vert_df.select("vert_id").unique()
    
    # Create mapping dataframe
    vert_ids = unique_verts["vert_id"].to_list()
    conn_ids = [component_map[vid] for vid in vert_ids]
    
    result_df = pl.DataFrame({
        "vert_id": vert_ids,
        "conn_id": conn_ids
    })
    
    # Get statistics
    n_components = result_df["conn_id"].n_unique()
    print(f"Number of connected components: {n_components}")
    
    # Show component size distribution
    component_sizes = result_df.group_by("conn_id").agg(pl.len().alias("size"))
    component_sizes = component_sizes.sort("size", descending=True)
    print("\nLargest components:")
    print(component_sizes.head(10))
    
    return result_df


def main():
    vert_df = pl.read_parquet("data/step4/vertices.parquet")
    edge_df = pl.read_parquet("data/step4/edges.parquet")
    
    print("Vertices:")
    print(vert_df)
    print("\nEdges:")
    print(edge_df)
    
    # Find connected components
    conn_df = find_connected_components(vert_df, edge_df)
    
    print("\nConnected components mapping:")
    print(conn_df)
    
    # Save result
    output_path = "data/step5/components.parquet"
    conn_df.write_parquet(output_path)
    print(f"\nSaved component mapping to: {output_path}")
    

def inspect_comp5():
    """
    Component 5 has 2.9 million nodes.
    Could something fishy be going on?
    """
    # Load data
    vert_df = pl.read_parquet("data/step4/vertices.parquet")
    edge_df = pl.read_parquet("data/step4/edges.parquet")
    conn_df = pl.read_parquet("data/step5/components.parquet")
    
    # Filter to component 5
    comp5_verts = conn_df.filter(pl.col("conn_id") == 5)
    comp5_vert_ids = comp5_verts["vert_id"]
    
    print(f"Component 5 has {len(comp5_verts)} vertices")
    
    # Get edges within component 5
    comp5_edges = edge_df.filter(
        pl.col("peer_id").is_in(comp5_vert_ids) | 
        pl.col("host_id").is_in(comp5_vert_ids)
    )
    
    print(f"Component 5 has {len(comp5_edges)} edges")
    
    # Calculate degree for each vertex (treating as undirected)
    # Count how many times each vertex appears as peer_id
    peer_counts = comp5_edges.group_by("peer_id").agg(
        pl.len().alias("peer_degree")
    ).rename({"peer_id": "vert_id"})
    
    # Count how many times each vertex appears as host_id
    host_counts = comp5_edges.group_by("host_id").agg(
        pl.len().alias("host_degree")
    ).rename({"host_id": "vert_id"})
    
    # Combine to get total degree
    degree_df = peer_counts.join(host_counts, on="vert_id", how="outer_coalesce")
    degree_df = degree_df.with_columns([
        pl.col("peer_degree").fill_null(0),
        pl.col("host_degree").fill_null(0)
    ])
    degree_df = degree_df.with_columns(
        (pl.col("peer_degree") + pl.col("host_degree")).alias("total_degree")
    )
    
    # Get top 10 most connected nodes
    top_nodes = degree_df.sort("total_degree", descending=True).head(10)
    
    # Join with vertex info to see what these nodes are
    top_nodes_info = top_nodes.join(vert_df, on="vert_id", how="left")
    
    print("\n" + "="*80)
    print("TOP 10 MOST CONNECTED NODES IN COMPONENT 5:")
    print("="*80)
    print(top_nodes_info.select(["vert_id", "word", "lang_code", "total_degree", "peer_degree", "host_degree"]))
    
    # Show some example edges for the most connected node
    if len(top_nodes_info) > 0:
        most_connected_id = top_nodes_info["vert_id"][0]
        most_connected_word = top_nodes_info["word"][0]
        most_connected_lang = top_nodes_info["lang_code"][0]
        
        print(f"\n" + "="*80)
        print(f"SAMPLE EDGES FOR MOST CONNECTED NODE:")
        print(f"vert_id={most_connected_id}, word='{most_connected_word}', lang='{most_connected_lang}'")
        print("="*80)
        
        # Get edges where this node is involved
        sample_edges = comp5_edges.filter(
            (pl.col("peer_id") == most_connected_id) | 
            (pl.col("host_id") == most_connected_id)
        ).head(20)
        
        # Join with vertex info for both peer and host
        sample_edges = sample_edges.join(
            vert_df.select(["vert_id", "word", "lang_code"]),
            left_on="peer_id",
            right_on="vert_id",
            how="left"
        ).rename({"word": "peer_word", "lang_code": "peer_lang"})
        
        sample_edges = sample_edges.join(
            vert_df.select(["vert_id", "word", "lang_code"]),
            left_on="host_id",
            right_on="vert_id",
            how="left"
        ).rename({"word": "host_word", "lang_code": "host_lang"})
        
        print(sample_edges.select([
            "edge_id", "template_name", "is_desc",
            "peer_id", "peer_word", "peer_lang",
            "host_id", "host_word", "host_lang"
        ]))

def exclude_leaves():
    vert_df = pl.read_parquet("data/step4/vertices.parquet")
    edge_df = pl.read_parquet("data/step4/edges_debug.parquet")
    # Calculate degree for each vertex (treating as undirected)
    # Count how many times each vertex appears as peer_id
    peer_counts = edge_df.group_by("peer_id").agg(
        pl.len().alias("peer_degree"),
    ).rename({"peer_id": "vert_id"})
    
    # Count how many times each vertex appears as host_id
    host_counts = edge_df.group_by("host_id").agg(
        pl.len().alias("host_degree"),
        pl.col("edge_type").filter(pl.col("edge_type") == "lemma").len().alias("host_lemma_degree")
    ).rename({"host_id": "vert_id"})
    
    # Combine to get total degree
    degree_df = peer_counts.join(host_counts, on="vert_id", how="outer_coalesce")
    degree_df = degree_df.with_columns([
        pl.col("peer_degree").fill_null(0),
        pl.col("host_lemma_degree").fill_null(0),
        pl.col("host_degree").fill_null(0)
    ])
    # degree_df = degree_df.with_columns(
    #     (pl.col("peer_degree") + pl.col("host_degree")).alias("total_degree")
    # )

    # if host_degree == host_lemma_degree == 1 and peer_degree == 0, then we have a leaf (likely a lemma)
    # which is not very useful

    leaf_df = degree_df.filter(
        (
            (pl.col("host_degree") == pl.col("host_lemma_degree")) & 
            (pl.col("host_lemma_degree") > 0) & 
            (pl.col("peer_degree") == 0)
        )
    )
    # .join(
    #     vert_df,
    #     on="vert_id",
    #     how="left",
    # ) 
    # 4.720 million

    print(f"Excluding {leaf_df.height} leaf nodes")

    vert_df = vert_df.join(
        leaf_df,
        on="vert_id",
        how="anti"
    )
    vert_df.write_parquet("data/step5/vertices.parquet")
    edge_df = edge_df.join(
        leaf_df,
        left_on="host_id",
        right_on="vert_id",
        how="anti"
    )
    edge_df.write_parquet("data/step5/edges_debug.parquet")

    edge_df = edge_df.drop("peer_word", "peer_lang", "palt_word", "palt_lang")
    edge_df.write_parquet("data/step5/edges.parquet")

    degree_df.join(
        leaf_df,
        on="vert_id",
        how="anti",
    ).write_parquet("data/step5/degrees.parquet")



if __name__ == "__main__":
    exclude_leaves()
    # main()
    # inspect_comp5()