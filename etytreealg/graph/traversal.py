import networkx as nx
from collections import deque
import polars as pl
from typing import Literal, Tuple, Set

EdgeDirection = Literal['outgoing', 'incoming', 'both']

def process_edges(
    edge_ids: list[int],
    edges_df: pl.DataFrame,
    visited: Set[Tuple[str, str]],
    queue: deque,
    graph: nx.Graph,
    max_vertices: int,
    template_rules,
    take_parent=True,
    self_id=None # debug
) -> None:
    """
    Process edges and update the graph, visited set, and queue.
    
    Args:
        edges_df: DataFrame of edges to process
        visited: Set of visited (word, lang) pairs
        queue: Queue for BFS
        graph: NetworkX graph to update
        max_vertices: Maximum number of vertices allowed
        outgoing: Whether these are outgoing edges
    """
    if edge_ids is None:
        return
    for edge_id in edge_ids:
        row = edges_df.row(edge_id, named=True)
        # Get source and target information

        if take_parent:
            neighbor = (row['parent_word'], row['parent_lang'])
            neighbor_id = row['parent_id']

            self_node = (row['host_word'], row['host_lang'])
            assert self_id == row['host_id']
        else:
            neighbor = (row['host_word'], row['host_lang'])
            neighbor_id = row['host_id']

            self_node = (row['parent_word'], row['parent_lang'])
            assert self_id == row['parent_id']

        edge_type = row['template_name']
        if not template_rules(edge_type):
            continue
        
        # Add the unvisited node to queue (either source or target)
        
        if neighbor_id not in visited and len(graph.nodes) < max_vertices:
            visited.add(neighbor_id)
            queue.append(neighbor_id)
            
            # Add nodes and edge to graph
            parent_label = f"{row['parent_word']} ({row['parent_lang']})"
            host_label = f"{row['host_word']} ({row['host_lang']})"
            graph.add_node(parent_label)
            graph.add_node(host_label)
            graph.add_edge( # reverse edge: we say that the parent produces the host
                parent_label,
                host_label,
                template=row['template_name']
            )

def explore_word_graph(
    edges_df: pl.DataFrame,
    vertex_df: pl.DataFrame,
    start_idx: int, 
    # start_word: str,
    # start_lang: str,
    lang_rules: dict[str, EdgeDirection],
    word_rules,
    template_rules,
    max_vertices: int = 20,
) -> nx.Graph:
    """
    Explore edges in a breadth-first manner starting from a given word/language pair.
    
    Args:
        edge_df: DataFrame containing edges with columns [source_word, source_lang, 
                target_word, target_lang, template_name]
        start_word: Initial word to start exploration
        start_lang: Language code of the initial word
        lang_rules: Dictionary specifying edge exploration rules for each language
                   e.g., {'es': 'outgoing', 'la': 'both', 'ine-pro': 'both'}
        max_vertices: Maximum number of vertices to include in the graph
    
    Returns:
        nx.Graph: Undirected graph of word relationships
    """
    # Initialize graph
    G = nx.DiGraph()
    
    # Queue for BFS
    queue = deque([start_idx])
    
    # Keep track of visited nodes
    visited: Set[int] = set()
    visited.add(start_idx)
    
    # Add first node
    (_, start_word, start_lang, _, _) = vertex_df.row(start_idx)
    G.add_node(f"{start_word} ({start_lang})", root=True)
    
    while queue and len(G.nodes) < max_vertices:
        current_idx = queue.popleft()

        _i, current_word, current_lang, ansc_eids, desc_eids = vertex_df.row(current_idx)
        assert current_idx == _i

        if not word_rules(current_word):
            continue
        
        # Get the rule for current language
        direction = lang_rules(current_lang)
        
        # Find and process edges based on language rules
        if direction in ('ancestors', 'both'): # outgoing
            # vertices is faster because we get the adjacency list
            process_edges(ansc_eids, edges_df, visited, queue, G, max_vertices, template_rules, take_parent=True, self_id=current_idx)
            
        if direction in ('descendants', 'both'): # incoming
            process_edges(desc_eids, edges_df, visited, queue, G, max_vertices, template_rules, take_parent=False, self_id=current_idx)


    return G


# Create graph
def lang_rules(langcode):
    rules = {
        'es': 'ancestors',
        'osp': 'ancestors',
        'la': 'both',
        'enm': 'both',
        # 'ine-pro': 'both',
        # 'gmw-pro': 'both',
    }
    if langcode in rules:
        return rules[langcode]
    if '-pro' in langcode:
        return 'both'
    return None

def _word_rules(x):
    if '-' in x: 
        # do not expand prefixes or suffixes
        return False
    return True

def _template_rules(x):
    if x in ['cog']:
        return False
    return True

def prune_leaves(
    G: nx.Graph,
    keep_langs: set[str],
    max_iterations: int = 10
) -> nx.Graph:
    """
    Iteratively remove leaf nodes whose languages are not in keep_langs.
    Continues until no more nodes can be removed or max_iterations is reached.
    
    Args:
        G: NetworkX graph where nodes are labeled as "word (lang)"
        keep_langs: Set of language codes to preserve
        max_iterations: Maximum number of pruning iterations
    
    Returns:
        nx.Graph: Pruned copy of the input graph
    """
    # Work with a copy of the graph
    H = G.copy()
    
    for _ in range(max_iterations):
        # Find leaves (nodes with degree 1)
        leaves = [node for node, degree in H.degree() if degree == 1]
        
        # Track if any leaves were removed this iteration
        removed = False
        
        for leaf in leaves:
            # Extract language code from node label (format: "word (lang)")
            lang = leaf.split('(')[1].rstrip(')')
            
            # the root is safe
            if H.nodes[leaf].get('root', False):
                continue

            # Remove if language not in keep set
            if lang not in keep_langs:
                H.remove_node(leaf)
                removed = True
        
        # If no leaves were removed, we're done
        if not removed:
            break
    
    return H

def graph_sugiyama_improved(G):
    import networkx as nx
    import grandalf
    from grandalf.layouts import SugiyamaLayout
    import matplotlib.pyplot as plt
    
    g = grandalf.utils.convert_nextworkx_graph_to_grandalf(G)
    
    class defaultview(object):
        def __init__(self):
            # Increase the default spacing between nodes
            self.w = 50  # Increased from 10
            self.h = 30  # Increased from 10
    
    for v in g.C[0].sV:
        v.view = defaultview()
    
    sug = SugiyamaLayout(g.C[0])
    # Configure layout parameters
    sug.dx = 100  # Horizontal spacing between nodes
    sug.dy = 50   # Vertical spacing between layers
    sug.init_all()
    sug.draw()
    
    # Extract positions and scale them for better visualization
    poses = {v.data: (v.view.xy[0] * 1.5, -v.view.xy[1]) for v in g.C[0].sV}
    
    # Create a larger figure
    plt.figure(figsize=(50, 15))
    
    # Create node color list based on language
    node_colors = []
    for node in G.nodes():
        lang = node.split('(')[1].rstrip(')')
        if lang == 'en':
            node_colors.append('lightgreen')
        # root is blue
        elif G.nodes[node].get('root', False):
            node_colors.append('red')
        else:
            node_colors.append('lightblue')

    # Draw with modified parameters
    nx.draw(G, pos=poses,
           with_labels=True,
           node_size=2000,        # Larger nodes
           node_color=node_colors,
           font_size=10,
           font_weight='bold',
           width=1.5,            # Thicker edges
           edge_color='gray',
           arrows=True,
           arrowsize=20)
    
    plt.margins(x=0.2)  # Add some padding around the graph
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    vertex_df = pl.read_parquet('data/parquet/spanish_vertices.parquet')
    edges_df = pl.read_parquet('data/parquet/spanish_edges.parquet')

    starter = vertex_df.filter((pl.col('lang') == 'es') & (pl.col('word') == 'escoger'))['vertex_id'][0]
    print(starter)
    graph = explore_word_graph(edges_df, vertex_df, starter, 
                               lang_rules=lang_rules, word_rules=_word_rules, template_rules=_template_rules, max_vertices=100)
    pruned_graph = prune_leaves(graph, {'en'}, max_iterations=10) # {'en', 'es', 'osp', 'la', 'enm', 'ine-pro', 'gmw-pro'})
    graph_sugiyama_improved(pruned_graph)
    # x = input("Press Enter to exit")
    # print(x)