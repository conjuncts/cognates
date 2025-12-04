import networkx as nx
import matplotlib.pyplot as plt
import polars as pl

from etytreealg.graph.layout import visualize_language_inheritance_graph


def produce_graph():
    df = pl.read_parquet("data/step3/language_inh.parquet").select("lang", "origin_lang")
    df = df.group_by("lang", "origin_lang").len().filter(
        pl.col("len") > 40
    )
    print(df)

    # Create a directed graph
    G = nx.DiGraph()

    # Add edges with weights based on count
    for row in df.iter_rows(named=True):
        G.add_edge(row['origin_lang'], row['lang'], weight=row['len'])
    
    return G


def filter_by_language(G, language="Proto-Indo-European"):
    descendants = nx.descendants(G, language)
    nodes_to_keep = descendants | {language}
    return G.subgraph(nodes_to_keep).copy()


def main():
    G = produce_graph()

    # root = "Proto-Indo-European"
    root = "Proto-Germanic"
    # root = "Proto-West Germanic"
    G = filter_by_language(G, language=root)

    # Create visualization
    fig, ax = visualize_language_inheritance_graph(G, root, figsize=(20, 16))
    plt.show()

if __name__ == "__main__":
    main()