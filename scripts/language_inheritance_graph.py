"""
Create a graph visualization showing language inheritance relationships
Based on the etymology data analysis from flat_script4_language_relations.py
"""

from typing import Literal
import polars as pl
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import numpy as np

def load_language_relations():
    """Load and process the language inheritance data"""
    ety_df = pl.read_parquet('data/step3/ety_expanded_flat.parquet')
    temp_df = pl.read_parquet('data/step3/templates_flat.parquet')
    langcodes = pl.read_parquet('data/step3/langcodes_flat.parquet')
    
    # Filter for inheritance templates
    applicable = temp_df.filter(
        pl.col('template_name').is_in(['inherited', 'inh']) &
        (pl.col('key') == 'args.2')
    )
    
    applicable = applicable.pivot(
        index='entry_id',
        on='key',
        values='value',
        aggregate_function='first'
    )
    
    # Join with etymology data and language codes
    applicable = applicable.join(
        ety_df.select(['entry_id', 'word', 'lang']), 
        on='entry_id'
    )
    
    applicable = applicable.join(
        langcodes.select(['code', 'name']).rename({'code': 'args.2', 'name': 'origin_lang'}),
        on='args.2',
    )

    # Relevance: determine language relevance based on number of entries in that language
    relevance = ety_df.group_by('lang').len().rename({'len': 'relevance'})
    
    return applicable, relevance

def create_inheritance_graph(lang_relations, min_count=5, focus_languages=None):
    """Create a directed graph of language inheritance relationships"""
    
    # Aggregate the relationships
    relations_agg = lang_relations.group_by(['lang', 'origin_lang']).len(name='count').sort('count', descending=True)
    
    # Filter by minimum count to reduce noise
    relations_filtered = relations_agg.filter(pl.col('count') >= min_count)
    
    # If focus languages specified, filter to include only those
    if focus_languages:
        relations_filtered = relations_filtered.filter(
            pl.col('lang').is_in(focus_languages) | 
            pl.col('origin_lang').is_in(focus_languages)
        )
    
    print(f"Creating graph with {len(relations_filtered)} relationships")
    
    # Create directed graph
    G = nx.DiGraph()
    
    for row in relations_filtered.iter_rows(named=True):
        origin = row['origin_lang']
        target = row['lang']
        count = row['count']
        
        G.add_edge(origin, target, weight=count)
    
    return G, relations_filtered

def categorize_languages(languages):
    """Categorize languages by type/era for coloring"""
    categories = {
        'proto': ['Proto-Germanic', 'Proto-West Germanic', 'Proto-Indo-European', 'Proto-Celtic'],
        'old': ['Old English', 'Old French', 'Old Norse', 'Old High German', 'Old Spanish', 'Old Italian'],
        'middle': ['Middle English', 'Middle French', 'Middle High German', 'Northern Middle English'],
        'latin': ['Latin', 'Late Latin', 'Vulgar Latin', 'Medieval Latin'],
        'modern': ['English', 'French', 'German', 'Spanish', 'Italian', 'Dutch', 'Swedish', 'Norwegian']
    }
    
    lang_categories = {}
    colors = {
        'proto': '#FF6B6B',      # Red
        'old': '#4ECDC4',        # Teal
        'middle': '#45B7D1',     # Blue
        'latin': '#96CEB4',      # Green
        'modern': '#FFEAA7',     # Yellow
        'other': '#DDA0DD'       # Plum
    }
    
    for lang in languages:
        categorized = False
        for category, lang_list in categories.items():
            if any(keyword in lang for keyword in lang_list):
                lang_categories[lang] = colors[category]
                categorized = True
                break
        if not categorized:
            lang_categories[lang] = colors['other']
    
    return lang_categories, colors

def hierarchical_layout(G: nx.DiGraph):
    """
    https://stackoverflow.com/a/76215030/29032885
    """
    G = G.copy()

    for layer, nodes in enumerate(reversed(tuple(nx.topological_generations(G)))):
        # `multipartite_layout` expects the layer as a node attribute, so add the
        # numeric layer value as a node attribute
        for node in nodes:
            G.nodes[node]["layer"] = layer

    # Compute the multipartite_layout using the "layer" node attribute
    pos = nx.multipartite_layout(G, subset_key="layer", align='horizontal')
    return pos
    # fig, ax = plt.subplots()
    # nx.draw_networkx(G, pos=pos, ax=ax)
    # ax.set_title("Tree layout in topological order")
    # fig.tight_layout()
    # plt.show()

def noisy_hierarchical_layout(G: nx.DiGraph, noise_factor=0.3, seed=42):
    """
    Create a hierarchical layout with random y-perturbation within layers
    and horizontal re-spacing to use full width based on widest layer
    
    Args:
        G: The directed graph
        noise_factor: Controls the amount of random perturbation (0-1, where 1 = full layer height)
        seed: Random seed for reproducibility
    """
    np.random.seed(seed)
    
    # Start with hierarchical layout
    pos = hierarchical_layout(G)
    
    # Group nodes by layer (y-coordinate)
    layers = defaultdict(list)
    for node, (x, y) in pos.items():
        layers[y].append(node)
    
    # Find the width of the widest layer to use as reference
    max_layer_width = max(len(nodes) for nodes in layers.values())
    
    # Get the original x-coordinate range
    all_x_coords = [x for x, y in pos.values()]
    min_x, max_x = min(all_x_coords), max(all_x_coords)
    full_width = max_x - min_x if max_x > min_x else 1.0
    
    # Redistribute nodes horizontally within each layer
    for y_coord, nodes in layers.items():
        num_nodes = len(nodes)
        if num_nodes == 1:
            # Single node centered
            pos[nodes[0]] = (min_x + full_width / 2, pos[nodes[0]][1])
        else:
            # Sort nodes by original x-coordinate to maintain relative order
            nodes_with_x = [(node, pos[node][0]) for node in nodes]
            nodes_with_x.sort(key=lambda x: x[1])
            
            # Redistribute evenly across full width
            for i, (node, _) in enumerate(nodes_with_x):
                new_x = min_x + (i / (num_nodes - 1)) * full_width
                pos[node] = (new_x, pos[node][1])
    
    # Calculate layer spacing for y-noise
    y_coords = sorted(layers.keys())
    if len(y_coords) > 1:
        layer_spacing = min(y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1))
    else:
        layer_spacing = 1.0
    
    # Add noise to y-coordinates within each layer
    max_noise = layer_spacing * noise_factor * 0.5  # 0.5 to keep noise symmetric around center
    
    for y_coord, nodes in layers.items():
        for node in nodes:
            # Add random perturbation to y-coordinate
            noise = np.random.uniform(-max_noise, max_noise)
            pos[node] = (pos[node][0], pos[node][1] + noise)
    
    return pos

def spring_with_gravity(G, gravity_strength=0.1, vertical=False, **kwargs):
    pos = nx.spring_layout(G, **kwargs)

    # Apply gravity along x (horizontal) or y (vertical)
    for node in pos:
        degree = G.in_degree(node) - G.out_degree(node)
        gravity_bias = gravity_strength * degree  # bias based on direction

        if vertical:
            pos[node][1] -= gravity_bias
        else:
            pos[node][0] += gravity_bias

    return pos

def visualize_inheritance_graph(
        G, 
        relevance_df,
        title="Language Inheritance Graph", 
        layout: Literal["hier", "spring", "gravity", "noisy-hier"] = "noisy-hier"):
    """Create a visualization of the language inheritance graph"""
    
    plt.figure(figsize=(16, 10))
    
    # Get node colors
    languages = list(G.nodes())
    lang_colors, color_legend = categorize_languages(languages)
    node_colors = [lang_colors[lang] for lang in languages]
    
    # Calculate node sizes based on relevance (number of entries in that language)
    relevance_dict = {row['lang']: row['relevance'] for row in relevance_df.iter_rows(named=True)}
    
    # Get relevance values for nodes, defaulting to 1 if not found
    relevance_values = [relevance_dict.get(node, 1) for node in languages]
    max_relevance = max(relevance_values) if relevance_values else 1
    min_relevance = min(relevance_values) if relevance_values else 1
    
    # Scale node sizes based on relevance (log scale for better visualization)
    min_node_size = 50
    max_node_size = 800
    
    if max_relevance > min_relevance:
        # Use log scale to prevent very large nodes from dominating
        log_relevance = [np.log(val + 1) for val in relevance_values]  # +1 to avoid log(0)
        max_log = max(log_relevance)
        min_log = min(log_relevance)
        
        node_sizes = [min_node_size + (log_val - min_log) / (max_log - min_log) * (max_node_size - min_node_size) 
                     for log_val in log_relevance]
    else:
        node_sizes = [min_node_size] * len(languages)
    
    # Use hierarchical layout
    if layout == "hier":
        pos = hierarchical_layout(G)
    elif layout == "noisy-hier":
        pos = noisy_hierarchical_layout(G, noise_factor=0.5, seed=42)
    elif layout == "spring":
        pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
    elif layout == "gravity":
        # pos = spring_with_gravity(G, gravity_strength=0.1, vertical=False, seed=42)
        pos = hierarchical_layout(G)
        pos = nx.spring_layout(G, pos=pos, k=0.5, iterations=1, seed=42)
    else:
        pos = nx.random_layout(G, seed=42)

    
    # Draw edges with varying thickness based on count
    edges = G.edges(data=True)
    edge_weights = [edge[2]['weight'] for edge in edges]
    max_weight = max(edge_weights) if edge_weights else 1
    min_width = 0.5
    max_width = 15  # Increased from 5 to 15
    
    edge_widths = [min_width + (weight / max_weight) * (max_width - min_width) 
                   for weight in edge_weights]
    
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.6, 
                          arrowsize=20, edge_color='gray')
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=node_sizes, alpha=0.8)
    
    # Add labels with font size and weight proportional to node size
    # Calculate font sizes and weights based on node sizes
    min_font_size = 6
    max_font_size = 12
    min_node_size = min(node_sizes)
    max_node_size = max(node_sizes)
    
    # Create font sizes proportional to node sizes
    font_sizes = {}
    font_weights = {}
    for i, node in enumerate(languages):
        # Normalize node size to 0-1 range
        if max_node_size > min_node_size:
            size_ratio = (node_sizes[i] - min_node_size) / (max_node_size - min_node_size)
        else:
            size_ratio = 0.5
        
        # Calculate font size
        font_size = min_font_size + size_ratio * (max_font_size - min_font_size)
        font_sizes[node] = font_size
        
        # Calculate font weight (map to matplotlib weight values)
        # Weight ranges from 'normal' (400) to 'bold' (700)
        weight_value = 400 + size_ratio * 300  # 400 to 700
        font_weights[node] = weight_value
    
    # Draw labels individually with varying font sizes and weights
    for node in languages:
        nx.draw_networkx_labels(G, pos, labels={node: node}, 
                              font_size=font_sizes[node], 
                              font_weight=font_weights[node])
    
    # Create legend
    legend_elements = []
    for category, color in color_legend.items():
        if category != 'other':  # Skip 'other' in legend for clarity
            legend_elements.append(mpatches.Patch(color=color, label=category.title()))
    
    plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))
    
    plt.title(title, fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    return plt

def create_focused_visualizations(lang_relations: pl.DataFrame, relevance: pl.DataFrame):
    """Create several focused visualizations"""
    
    # 1. English inheritance tree
    # print("Creating English inheritance visualization...")
    # english_relations = lang_relations.filter(pl.col('lang') == 'English')
    # G_en, relations_en = create_inheritance_graph(english_relations, min_count=1)
    
    # plt1 = visualize_inheritance_graph(G_en, relations_en, 
    #                                  "English Language Inheritance")
    # plt1.savefig('data/english_inheritance.png', dpi=300, bbox_inches='tight')
    # plt1.show()
    
    # 2. Top languages overall
    print("Creating overall language relationships...")
    top_langs = lang_relations.group_by('lang').len(name='count').sort('count', descending=True).head(80)
    top_lang_names = top_langs['lang'].to_list()
    
    G_top, relations_top = create_inheritance_graph(lang_relations, min_count=10, 
                                                   focus_languages=top_lang_names)
    
    plt2 = visualize_inheritance_graph(G_top, relevance,
                                       # relations_top, 
                                     "Major Language Inheritance Relationships")
    plt2.savefig('data/major_language_inheritance.png', dpi=300, bbox_inches='tight')
    plt2.show()
    
    # 3. Germanic language family
    # print("Creating Germanic language family tree...")
    # germanic_keywords = ['English', 'German', 'Dutch', 'Swedish', 'Norwegian', 
    #                     'Proto-Germanic', 'Proto-West Germanic', 'Old English', 
    #                     'Middle English', 'Old High German', 'Middle High German']
    
    # germanic_relations = lang_relations.filter(
    #     pl.col('lang').str.contains('|'.join(germanic_keywords)) |
    #     pl.col('origin_lang').str.contains('|'.join(germanic_keywords))
    # )
    
    # G_germ, relations_germ = create_inheritance_graph(germanic_relations, min_count=1)
    
    # plt3 = visualize_inheritance_graph(G_germ, relations_germ, 
    #                                  "Germanic Language Family Tree")
    # plt3.savefig('data/germanic_language_tree.png', dpi=300, bbox_inches='tight')
    # plt3.show()

def print_statistics(lang_relations):
    """Print interesting statistics about the language relationships"""
    
    print("\n" + "="*50)
    print("LANGUAGE INHERITANCE STATISTICS")
    print("="*50)
    
    # Total relationships
    total_relations = len(lang_relations)
    unique_languages = lang_relations['lang'].n_unique()
    unique_origins = lang_relations['origin_lang'].n_unique()
    
    print(f"Total inheritance relationships: {total_relations:,}")
    print(f"Unique target languages: {unique_languages}")
    print(f"Unique source languages: {unique_origins}")
    
    # Most prolific source languages
    print("\nTop 10 Source Languages (languages others inherit from):")
    source_counts = lang_relations.group_by('origin_lang').len(name='count').sort('count', descending=True).head(10)
    for row in source_counts.iter_rows(named=True):
        print(f"  {row['origin_lang']}: {row['count']:,} inheritances")
    
    # Languages with most diverse origins
    print("\nTop 10 Target Languages (languages that inherit from others):")
    target_counts = lang_relations.group_by('lang').len(name='count').sort('count', descending=True).head(10)
    for row in target_counts.iter_rows(named=True):
        print(f"  {row['lang']}: {row['count']:,} inherited words")
    
    # Most common specific relationships
    print("\nTop 10 Specific Language Pairs:")
    pair_counts = lang_relations.group_by(['origin_lang', 'lang']).len(name='count').sort('count', descending=True).head(10)
    for row in pair_counts.iter_rows(named=True):
        print(f"  {row['origin_lang']} → {row['lang']}: {row['count']:,} words")

def main():
    """Main function to run the analysis and create visualizations"""
    
    print("Loading language inheritance data...")
    lang_relations, relevance = load_language_relations()

    print(f"Loaded {len(lang_relations):,} language inheritance relationships")
    
    # Print statistics
    # print_statistics(lang_relations)
    
    # Create visualizations
    create_focused_visualizations(lang_relations, relevance)
    
    print("\nVisualization complete! Check the generated PNG files.")

if __name__ == "__main__":
    main()
