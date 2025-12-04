import networkx as nx
import matplotlib.pyplot as plt

from etytreealg.graph.hierarchy import hierarchy_pos_dyn, spanning_tree_by_topo_sort




def visualize_language_inheritance_graph(G, root, figsize=(20, 16), transpose=True):
    """
    Visualize a language inheritance graph with weighted edges.
    
    Args:
        G: NetworkX DiGraph with 'weight' attribute on edges representing inheritance counts
        root: Root node for the spanning tree layout
        figsize: Tuple of (width, height) for the figure size
        transpose: If True, transpose the layout to be horizontal (LTR)
    
    Returns:
        fig, ax: matplotlib figure and axes objects
    """
    # Create visualization
    fig, ax = plt.subplots(figsize=figsize)

    T, nontree_edges = spanning_tree_by_topo_sort(G)
    pos = hierarchy_pos_dyn(T, root=root)

    # transpose, because text is LTR
    if transpose:
        for k, v in pos.items():
            pos[k] = (-v[1], v[0])

    # Draw the graph
    # Scale edge widths based on count (normalized for visibility)
    edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in edges]
    max_weight = max(weights)
    min_weight = min(weights)

    # Normalize weights for edge width (0.5 to 5.0)
    edge_widths = [0.5 + 4.5 * (w - min_weight) / (max_weight - min_weight) if max_weight > min_weight else 1.0 for w in weights]

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=100, alpha=0.7, ax=ax)

    # Draw edges with varying widths
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.5, edge_color='gray', ax=ax)

    # Draw labels (only for nodes with high degree to avoid clutter)
    degree_dict = dict(G.degree())
    important_nodes = {node: node for node, deg in degree_dict.items()}
    nx.draw_networkx_labels(G, pos, labels=important_nodes, font_size=8, font_weight='bold', ax=ax)

    ax.axis('off')
    fig.tight_layout()
    
    return fig, ax

