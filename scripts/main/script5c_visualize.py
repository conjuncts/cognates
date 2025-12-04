import polars as pl
import networkx as nx
from collections import deque
import matplotlib.pyplot as plt
from etytreealg.graph.layout import visualize_language_inheritance_graph


def load_largest_component():
    """Load vertices and edges for the largest connected component."""
    print("Loading data...")
    vert_df = pl.read_parquet("data/step5/vertices.parquet")
    edge_df = pl.read_parquet("data/step5/edges_debug.parquet")
    conn_df = pl.read_parquet("data/step5/components.parquet")
    
    # Get the largest component ID (should be 9 with 1.57M nodes)
    largest_comp_id = conn_df.group_by("conn_id").agg(
        pl.len().alias("size")
    ).sort("size", descending=True).select("conn_id").head(1).item()
    
    print(f"Largest component ID: {largest_comp_id}")
    
    # Filter to only vertices in the largest component
    comp_verts = conn_df.filter(pl.col("conn_id") == largest_comp_id)
    comp_vert_ids = set(comp_verts["vert_id"].to_list())
    
    # Filter vertices and edges
    vert_df = vert_df.filter(pl.col("vert_id").is_in(comp_vert_ids))
    edge_df = edge_df.filter(
        pl.col("peer_id").is_in(comp_vert_ids) & 
        pl.col("host_id").is_in(comp_vert_ids)
    )
    
    print(f"Loaded {len(vert_df)} vertices and {len(edge_df)} edges from largest component")
    
    return vert_df, edge_df, comp_vert_ids


def find_word_vertex(vert_df, word):
    """Find vertex ID for a given word."""
    # Try exact match first
    matches = vert_df.filter(pl.col("word") == word)
    
    if len(matches) == 0:
        # Try case-insensitive match
        matches = vert_df.filter(pl.col("word").str.to_lowercase() == word.lower())
    
    if len(matches) == 0:
        # Try partial match
        matches = vert_df.filter(pl.col("word").str.contains(f"(?i){word}"))
        
        if len(matches) == 0:
            print(f"No matches found for '{word}'")
            return None
        
        print(f"\nFound {len(matches)} partial matches:")
        for i, row in enumerate(matches.head(20).iter_rows(named=True)):
            print(f"  {i+1}. {row['word']} (lang: {row['lang_code']}, vert_id: {row['vert_id']})")
        
        if len(matches) > 20:
            print(f"  ... and {len(matches) - 20} more")
        
        return None
    
    if len(matches) == 1:
        return matches["vert_id"][0]
    
    # Multiple exact matches - let user choose
    print(f"\nFound {len(matches)} exact matches:")
    for i, row in enumerate(matches.iter_rows(named=True)):
        print(f"  {i+1}. {row['word']} (lang: {row['lang_code']}, vert_id: {row['vert_id']})")
    
    choice = input(f"Enter choice (1-{len(matches)}): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(matches):
            return matches["vert_id"][idx]
    except ValueError:
        pass
    
    print("Invalid choice")
    return None


def build_bfs_dag(edge_df, vert_df, start_vert_id, max_depth):
    """
    Build a DAG using BFS from the starting vertex.
    All edges point outward from the root to maintain DAG structure.
    """
    print(f"\nBuilding BFS DAG from vertex {start_vert_id} with max depth {max_depth}...")
    
    # Create a mapping for quick edge lookups
    # We'll treat the graph as undirected for BFS traversal
    edges_from_peer = edge_df.select("peer_id", "host_id").rename({"peer_id": "from", "host_id": "to"})
    edges_from_host = edge_df.select("host_id", "peer_id").rename({"host_id": "from", "peer_id": "to"})
    all_edges = pl.concat([edges_from_peer, edges_from_host])
    
    # Group by source to get all neighbors
    edges_grouped = all_edges.group_by("from").agg(pl.col("to"))
    edge_dict = {row["from"]: set(row["to"]) for row in edges_grouped.iter_rows(named=True)}
    
    # BFS
    visited = {start_vert_id}
    queue = deque([(start_vert_id, 0)])
    bfs_edges = []  # (parent, child, depth)
    
    while queue:
        current_id, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        # Get neighbors
        neighbors = edge_dict.get(current_id, set())
        
        for neighbor_id in neighbors:
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append((neighbor_id, depth + 1))
                bfs_edges.append((current_id, neighbor_id, depth + 1))
    
    print(f"BFS found {len(visited)} vertices and {len(bfs_edges)} edges")
    
    # Create NetworkX DiGraph with edges pointing outward from root
    G = nx.DiGraph()
    
    # Add all vertices with their labels
    vert_subset = vert_df.filter(pl.col("vert_id").is_in(list(visited)))
    for row in vert_subset.iter_rows(named=True):
        G.add_node(row['vert_id'], word=row['word'], lang=row['lang_code'])
    
    # Add edges (all pointing away from root)
    for parent, child, depth in bfs_edges:
        G.add_edge(parent, child, weight=1)
    
    return G, visited


def explore_component():
    """Interactive exploration of the largest component."""
    vert_df, edge_df, comp_vert_ids = load_largest_component()
    
    print("\n" + "="*60)
    print("LARGEST COMPONENT EXPLORER")
    print("="*60)
    
    while True:
        print("\n" + "-"*60)
        word = input("\nEnter a word to start from (or 'quit' to exit): ").strip()
        
        if word.lower() in ['quit', 'q', 'exit']:
            break
        
        if not word:
            continue
        
        # Find the vertex
        vert_id = find_word_vertex(vert_df, word)
        
        if vert_id is None:
            continue
        
        # Get depth
        depth_str = input("Enter max depth (default 3): ").strip()
        try:
            max_depth = int(depth_str) if depth_str else 3
        except ValueError:
            print("Invalid depth, using default of 3")
            max_depth = 3
        
        # Build BFS DAG
        G, visited_nodes = build_bfs_dag(edge_df, vert_df, vert_id, max_depth)
        
        if len(G.nodes()) == 0:
            print("No graph could be built!")
            continue
        
        # Get the word for display
        start_word = vert_df.filter(pl.col("vert_id") == vert_id)["word"][0]
        
        print(f"\nVisualizing subgraph with {len(G.nodes())} nodes and {len(G.edges())} edges...")
        print(f"Root: {start_word} (vert_id: {vert_id})")
        
        # Create a mapping from vert_id to word#lang_code for node labels
        vert_subset = vert_df.filter(pl.col("vert_id").is_in(list(G.nodes())))
        node_labels = {}
        for row in vert_subset.iter_rows(named=True):
            node_labels[row['vert_id']] = f"{row['word']}#{row['lang_code']}"
        
        # Relabel the graph nodes with word#lang_code format
        G_labeled = nx.relabel_nodes(G, node_labels, copy=True)
        root_label = node_labels[vert_id]
        
        # Visualize
        try:
            fig, ax = visualize_language_inheritance_graph(G_labeled, root_label, figsize=(20, 16))
            plt.title(f"BFS Subgraph from '{start_word}' (depth={max_depth})", fontsize=16)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f"Error during visualization: {e}")
            import traceback
            traceback.print_exc()
    
    print("\nGoodbye!")


if __name__ == "__main__":
    explore_component()
