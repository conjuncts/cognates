import networkx as nx
import matplotlib.pyplot as plt
import polars as pl

from etytreealg.graph.layout import visualize_language_inheritance_graph


def produce_graph():
    df = pl.read_parquet("data/step3/language_inh.parquet").select("lang", "origin_lang")
    df = df.group_by("lang", "origin_lang").len().filter(
        pl.col("len") > 40
    )
    # print(df)

    # Create a directed graph
    G = nx.DiGraph()

    # Add edges with weights based on count
    for row in df.iter_rows(named=True):
        G.add_edge(row['origin_lang'], row['lang'], weight=row['len'])
    
    return G


def filter_by_language(G, language="Proto-Indo-European", plus_ancestors=False):
    descendants = nx.descendants(G, language)
    nodes_to_keep = descendants | {language}
    # ancestors = nx.ancestors(G, language)
    if plus_ancestors:
        ancestors = nx.ancestors(G, language)
        nodes_to_keep = descendants | ancestors | {language}
    return G.subgraph(nodes_to_keep).copy()


def main():
    G = produce_graph()

    # lang = "Proto-Indo-European"
    lang = "Proto-Germanic"
    # lang = "Proto-West Germanic"
    # lang = "Proto-Sino-Tibetan"
    lang = "Proto-Italic"
    lang = "Proto-Afroasiatic"
    lang = "Proto-Turkic"
    lang = "Proto-Japonic"
    lang = "Proto-Austroasiatic"
    lang = "Proto-Uralic"

    # plus_ancestors = True
    plus_ancestors = False
    G = filter_by_language(G, language=lang, plus_ancestors=plus_ancestors)

    # get root as all with in-degree 0
    roots = [n for n, d in G.in_degree() if d == 0]
    if len(roots) == 1:
        root = roots[0]
    else:
        print("Multiple roots found, using first:", roots)
        root = roots[0]

    # Create visualization
    fig, ax = visualize_language_inheritance_graph(G, root, figsize=(20, 16))
    plt.show()

if __name__ == "__main__":
    main()