
import networkx as nx
import random

# Source - https://stackoverflow.com/a/29597209
# Posted by Joel, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-15, License - CC BY-SA 4.0



def hierarchy_pos_dyn_forest(G, roots=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, leaf_width=10):
    '''
    Layout for a forest: compute dynamic subtree widths for each tree root and place
    roots side-by-side within the given width. Each tree is then laid out using the
    same proportional-width logic as in `hierarchy_pos_dyn`.

    :param G: a graph containing one or more disjoint trees (a forest)
    :param roots: optional list of root nodes. If None, roots are computed as nodes with in-degree 0
    :param width: horizontal space allocated for the entire forest
    :param vert_gap: gap between levels of hierarchy
    :param vert_loc: vertical location of roots
    :param xcenter: horizontal center location
    :param leaf_width: width allocated to each leaf node
    '''
    if not nx.is_forest(G):
        raise TypeError('cannot use hierarchy_pos_dyn_forest on a graph that is not a forest')

    if roots is None:
        # Find roots as nodes with in-degree 0
        roots = [n for n, d in G.in_degree() if d == 0]
        # If no in-degree-zero nodes (e.g. undirected forest), fall back to connected component representatives
        if not roots:
            if isinstance(G, nx.DiGraph):
                roots = [next(iter(c)) for c in nx.weakly_connected_components(G)]
            else:
                roots = [next(iter(c)) for c in nx.connected_components(G)]

    if not roots:
        raise ValueError("No roots found for forest layout")

    # Calculate widths for each subtree
    def _calculate_widths(node, parent=None):
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)

        if len(children) == 0:
            return {node: leaf_width}
        else:
            widths = {}
            total_width = 0
            for child in children:
                child_widths = _calculate_widths(child, parent=node)
                widths.update(child_widths)
                total_width += child_widths[child]
            widths[node] = total_width
            return widths

    # Compute widths for all roots and merge
    node_widths = {}
    root_widths = {}
    for root in roots:
        if root in node_widths:
            root_widths[root] = node_widths[root]
            continue
        submap = _calculate_widths(root)
        node_widths.update(submap)
        root_widths[root] = node_widths[root]

    # Calculate proportional width allocation for each root
    total_root_width = sum(root_widths.values())
    if total_root_width == 0:
        root_shares = {r: 1.0/len(roots) for r in roots}
    else:
        root_shares = {r: (root_widths[r] / total_root_width) for r in roots}

    # Recursive positioning function
    def _hierarchy_pos(root, width, vert_loc, xcenter, pos=None, parent=None):
        if pos is None:
            pos = {root: (xcenter, vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)

        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)

        if len(children) != 0:
            total_child_width = sum(node_widths.get(child, leaf_width) for child in children)
            if total_child_width == 0:
                dx = width / len(children)
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos(child, dx, vert_loc-vert_gap, nextx, pos=pos, parent=root)
            else:
                nextx = xcenter - width/2
                for child in children:
                    child_eff = node_widths.get(child, leaf_width)
                    child_width = width * (child_eff / total_child_width)
                    child_center = nextx + child_width/2
                    pos = _hierarchy_pos(child, child_width, vert_loc-vert_gap, child_center, pos=pos, parent=root)
                    nextx += child_width
        return pos

    # Position each root in the forest across the available width
    pos = {}
    nextx = xcenter - width/2
    for r in roots:
        share = root_shares.get(r, 1.0/len(roots))
        r_width = width * share
        r_center = nextx + r_width/2
        pos = _hierarchy_pos(r, r_width, vert_loc, r_center, pos=pos, parent=None)
        nextx += r_width

    return pos


def hierarchy_pos_dyn(G, root=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, leaf_width=10):
    """
    Modified from Joel's answer at https://stackoverflow.com/a/29597209. 
    Licensed under CC BY-SA 4.0

    Assigns each node a width based on their subtree size:
    1. For leaf node: leaf_width
    2. For internal node: sum of widths of children

    Nodes are positioned proportionally to their width rather than evenly spaced.

    :param G: the graph (must be a tree)
    :param root: the root node of current branch
    :param width: horizontal space allocated for this branch - avoids overlap with other branches
    :param vert_gap: gap between levels of hierarchy
    :param vert_loc: vertical location of root
    :param xcenter: horizontal location of root
    :param leaf_width: width allocated to each leaf node (default 0.1)
    """
    if not nx.is_tree(G):
        raise TypeError('cannot use hierarchy_pos on a graph that is not a tree')

    if root is None:
        if isinstance(G, nx.DiGraph):
            root = next(iter(nx.topological_sort(G)))  #allows back compatibility with nx version 1.11
        else:
            root = random.choice(list(G.nodes))

    # First pass: calculate width for each node
    def _calculate_widths(G, node, parent=None):
        """
        Calculate the width of each node's subtree.
        Leaf nodes get leaf_width, internal nodes get sum of children widths.
        Returns dict mapping node -> width
        """
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if len(children) == 0:
            # Leaf node
            return {node: leaf_width}
        else:
            # Internal node: recursively calculate children widths
            widths = {}
            total_width = 0
            for child in children:
                child_widths = _calculate_widths(G, child, parent=node)
                widths.update(child_widths)
                total_width += child_widths[child]
            widths[node] = total_width
            return widths
    
    node_widths = _calculate_widths(G, root)

    def _hierarchy_pos(G, root, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, pos = None, parent = None):
        """
        see hierarchy_pos docstring for most arguments

        pos: a dict saying where all nodes go if they have been assigned
        parent: parent of this branch. - only affects it if non-directed
        """
        if pos is None:
            pos = {root:(xcenter,vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)
        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)  
        if len(children)!=0:
            # Calculate total width of all children
            total_child_width = sum(node_widths[child] for child in children)
            
            # Position children proportionally to their widths
            nextx = xcenter - width/2
            for child in children:
                # Width allocated to this child proportional to its subtree width
                child_proportion = node_widths[child] / total_child_width
                child_width = width * child_proportion
                # Center of this child's allocated space
                child_center = nextx + child_width/2
                
                pos = _hierarchy_pos(G, child, width = child_width, vert_gap = vert_gap, 
                                    vert_loc = vert_loc-vert_gap, xcenter=child_center,
                                    pos=pos, parent = root)
                nextx += child_width
        return pos

            
    return _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)


def hierarchy_pos_dyn_compact(G, root=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, leaf_width=10):

    '''
    Compact hierarchical layout. Each node receives a "width tuple" describing
    the distribution of descendants by depth. Leaf nodes get (leaf_width,),
    internal nodes get (leaf_width,) prefixed to the elementwise sum of their children's tuples.

    The effective scalar width used for spacing is the max value of the tuple.

    This function computes the tuple widths first, then positions nodes proportionally
    to their effective widths.
    '''
    if not nx.is_tree(G):
        raise TypeError('cannot use hierarchy_pos on a graph that is not a tree')

    if root is None:
        if isinstance(G, nx.DiGraph):
            root = next(iter(nx.topological_sort(G)))
        else:
            root = random.choice(list(G.nodes))

    # helper to elementwise-sum two tuples (pad with zeros)
    def tuple_sum(a, b):
        maxlen = max(len(a), len(b))
        a_ext = list(a) + [0] * (maxlen - len(a))
        b_ext = list(b) + [0] * (maxlen - len(b))
        return tuple(x + y for x, y in zip(a_ext, b_ext))

    # First pass: compute tuple widths for every node
    def _calc_tuples(node, parent=None):
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)

        if len(children) == 0:
            return {node: (leaf_width,)}

        widths = {}
        summed = None
        for child in children:
            child_map = _calc_tuples(child, parent=node)
            widths.update(child_map)
            child_tuple = child_map[child]
            if summed is None:
                summed = child_tuple
            else:
                summed = tuple_sum(summed, child_tuple)
        # Prefix leaf_width to indicate this node itself
        # Use leaf_width as the leading element so that effective width reflects descendants as well.
        node_tuple = (leaf_width,) + (summed if summed is not None else ())
        widths[node] = node_tuple
        return widths

    node_tuples = _calc_tuples(root)

    # Effective scalar width for layout is the max of the tuple
    node_eff_width = {n: max(tup) if len(tup) > 0 else 0 for n, tup in node_tuples.items()}

    def _hierarchy_pos(G, root, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, pos = None, parent = None):
        if pos is None:
            pos = {root:(xcenter,vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)

        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)

        if len(children) != 0:
            # use effective widths for allocation
            effs = [node_eff_width.get(child, 1) for child in children]
            total_eff = sum(effs)
            if total_eff == 0:
                # fallback to equal spacing
                dx = width / len(children)
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos(G, child, width = dx, vert_gap = vert_gap,
                                        vert_loc = vert_loc-vert_gap, xcenter = nextx,
                                        pos=pos, parent = root)
            else:
                nextx = xcenter - width/2
                for child, eff in zip(children, effs):
                    child_width = width * (eff / total_eff)
                    child_center = nextx + child_width/2
                    pos = _hierarchy_pos(G, child, width = child_width, vert_gap = vert_gap,
                                        vert_loc = vert_loc-vert_gap, xcenter = child_center,
                                        pos=pos, parent = root)
                    nextx += child_width
        return pos

    return _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)

# Source - https://stackoverflow.com/a/29597209
# Posted by Joel, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-16, License - CC BY-SA 4.0

    
def hierarchy_pos_orig(G, root=None, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5):

    '''
    From Joel's answer at https://stackoverflow.com/a/29597209/2966723.  
    Licensed under Creative Commons Attribution-Share Alike 
    
    If the graph is a tree this will return the positions to plot this in a 
    hierarchical layout.
    
    G: the graph (must be a tree)
    
    root: the root node of current branch 
    - if the tree is directed and this is not given, 
      the root will be found and used
    - if the tree is directed and this is given, then 
      the positions will be just for the descendants of this node.
    - if the tree is undirected and not given, 
      then a random choice will be used.
    
    width: horizontal space allocated for this branch - avoids overlap with other branches
    
    vert_gap: gap between levels of hierarchy
    
    vert_loc: vertical location of root
    
    xcenter: horizontal location of root
    '''
    if not nx.is_tree(G):
        raise TypeError('cannot use hierarchy_pos on a graph that is not a tree')

    if root is None:
        if isinstance(G, nx.DiGraph):
            root = next(iter(nx.topological_sort(G)))  #allows back compatibility with nx version 1.11
        else:
            root = random.choice(list(G.nodes))

    def _hierarchy_pos(G, root, width=1., vert_gap = 0.2, vert_loc = 0, xcenter = 0.5, pos = None, parent = None):
        '''
        see hierarchy_pos docstring for most arguments

        pos: a dict saying where all nodes go if they have been assigned
        parent: parent of this branch. - only affects it if non-directed

        '''
    
        if pos is None:
            pos = {root:(xcenter,vert_loc)}
        else:
            pos[root] = (xcenter, vert_loc)
        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)  
        if len(children)!=0:
            dx = width/len(children) 
            nextx = xcenter - width/2 - dx/2
            for child in children:
                nextx += dx
                pos = _hierarchy_pos(G,child, width = dx, vert_gap = vert_gap, 
                                    vert_loc = vert_loc-vert_gap, xcenter=nextx,
                                    pos=pos, parent = root)
        return pos

            
    return _hierarchy_pos(G, root, width, vert_gap, vert_loc, xcenter)

# Source - https://stackoverflow.com/a/42723250
# Posted by burubum, modified by community. See post 'Timeline' for change history
# Retrieved 2025-11-16, License - CC BY-SA 4.0

def hierarchy_pos_equi(G, root, levels=None, width=1., height=1.):
    '''If there is a cycle that is reachable from root, then this will see infinite recursion.
       G: the graph
       root: the root node
       levels: a dictionary
               key: level number (starting from 0)
               value: number of nodes in this level
       width: horizontal space allocated for drawing
       height: vertical space allocated for drawing'''
    TOTAL = "total"
    CURRENT = "current"
    def make_levels(levels, node=root, currentLevel=0, parent=None):
        """Compute the number of nodes for each level
        """
        if not currentLevel in levels:
            levels[currentLevel] = {TOTAL : 0, CURRENT : 0}
        levels[currentLevel][TOTAL] += 1
        neighbors = G.neighbors(node)
        for neighbor in neighbors:
            if not neighbor == parent:
                levels =  make_levels(levels, neighbor, currentLevel + 1, node)
        return levels

    def make_pos(pos, node=root, currentLevel=0, parent=None, vert_loc=0):
        dx = 1/levels[currentLevel][TOTAL]
        left = dx/2
        pos[node] = ((left + dx*levels[currentLevel][CURRENT])*width, vert_loc)
        levels[currentLevel][CURRENT] += 1
        neighbors = G.neighbors(node)
        for neighbor in neighbors:
            if not neighbor == parent:
                pos = make_pos(pos, neighbor, currentLevel + 1, node, vert_loc-vert_gap)
        return pos
    if levels is None:
        levels = make_levels({})
    else:
        levels = {l:{TOTAL: levels[l], CURRENT:0} for l in levels}
    vert_gap = height / (max([l for l in levels])+1)
    return make_pos({})


def spanning_tree_by_topo_sort(G: nx.DiGraph) -> tuple[nx.DiGraph, list[tuple]]:
    """
    Construct spanning tree (T) and non-tree edges from a DAG G
    by performing a topological sort. When adding edges, always connect
    a child to its youngest parent (the one with the greatest depth).

    Returns:
        T: A directed tree (DiGraph) containing the spanning tree edges
        nontree_edges: List of tuples (u, v, edge_data)
    """
    T = nx.DiGraph()
    nontree_edges = []
    depth = {}
    
    for node in nx.topological_sort(G):
        parents = list(G.predecessors(node))
        
        if not parents:
            # This is a root node
            T.add_node(node, depth=0)
            depth[node] = 0
        else:
            # parents MUST already be in T because of topo sort
            
            # Choose the deepest parent
            deepest_parent = max(parents, key=lambda p: depth[p])
            node_depth = depth[deepest_parent] + 1
            
            T.add_node(node, depth=node_depth)
            depth[node] = node_depth
            T.add_edge(deepest_parent, node, **G[deepest_parent][node])
            
            # All other edges from parents are non-tree edges
            for parent in parents:
                if parent != deepest_parent:
                    nontree_edges.append((parent, node, G[parent][node]))
    
    return T, nontree_edges
