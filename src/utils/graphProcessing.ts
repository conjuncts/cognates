import { CytoData, APIResponse, CytoNode, CytoLink } from '../types';
import { transitive_reduction } from './transitiveReduction';

function generateAdjacencyList(graphData: CytoData) {
  const adjacencyList = {} as Record<string, string[]>;
  const reverseAdjacencyList = {} as Record<string, string[]>;

  // Initialize adjacency list with empty arrays for each node
  graphData.nodes.forEach((node) => {
      adjacencyList[node.data.id] = [];
      reverseAdjacencyList[node.data.id] = [];
  });

  // Populate adjacency list using edges
  graphData.edges.forEach((edge) => {
      const { source, target } = edge.data;
      adjacencyList[source].push(target);
      // Uncomment the next line for undirected graphs:
      // adjacencyList[target].push(source);
      reverseAdjacencyList[target].push(source);
  });

  return { adjacencyList, reverseAdjacencyList };
}

// graph: CytoData, 
/**
 * 
 * @param root 
 * @param id2node 
 * @param adjacencyList a dictionary of node id to a list of neighbor node ids
 * @param reverseAdjacencyList a dictionary of node id to a list of neighbor node ids
 * @param expected_max_depth 
 */
const BFS = (root: CytoNode, id2node: Record<string, CytoNode>, 
    adjacencyList: Record<string, string[]>, reverseAdjacencyList: Record<string, string[]>, 
    expected_max_depth=4) => {
  const visited = new Set<string>();
  const queue = [root];
  root.data.depth = 0;
  // const depth = {[root.data.id]: 0};
  while (queue.length > 0) {
    const node = queue.shift()!;
    
    if(visited.has(node.data.id)) continue;
    
    // for (let edge of graph.edges) {
    //   let neighbor;
    //   if (edge.data.source === node.data.id) {
    //     neighbor = graph.nodes.find(n => n.data.id === edge.data.target)!;
    //     // depth[targetNode.data.id] = depth[node.data.id] + 1;
        
    //   } else if(edge.data.target === node.data.id) {
    //     neighbor = graph.nodes.find(n => n.data.id === edge.data.source)!;
    //     // depth[sourceNode.data.id] = depth[node.data.id] + 1;
    //   } else {
    //     continue;
    //   }
    for (let neighborId of adjacencyList[node.data.id].concat(reverseAdjacencyList[node.data.id])) {
      const neighbor = id2node[neighborId];
      if(neighbor.data.depth === undefined) {
        neighbor.data.depth = node.data.depth! + 1;
        // console.log(neighbor.data.depth);
        if(neighbor.data.depth > expected_max_depth) {
          console.log('Unexpected depth', neighbor.data.depth);
        }
        queue.push(neighbor); // the queue always contains nodes with depth defined
        // visited.add(node.data.id);
      }
    }
  }

  // apply depths to nodes
  // for (let node of graph.nodes) {
  //   node.data.depth = depth[node.data.id];
  // }
  // return depth;
  
}


export const processDataForGraph = (apiData: APIResponse): CytoData => {
  const nodes = apiData.vertices.map((node, i) => ({
    data: {
      id: String(node[0]),
      label: `${node[1]} (${node[2]})`,
      word: node[1],
      lang: node[2],
      root: i === 0,
      depth: undefined, // i === 0 ? 0 : undefined,
    }
  }));

  const edgeSet = new Set<[number, number]>();
  const edges = [];
  for (let edge of apiData.edges) {
    const key = (edge[2] ? [edge[0], edge[1]] : [edge[1], edge[0]]) as [number, number];
    if (!edgeSet.has(key)) {
      edgeSet.add(key);
      edges.push({
        data: {
          source: String(key[0]),
          target: String(key[1]),
        }
      });
    }
  }

  const graphData = { nodes, edges };

  const { adjacencyList, reverseAdjacencyList } = generateAdjacencyList(graphData);

  const id2node = {} as Record<string, CytoNode>;
  for (let node of nodes) {
    id2node[node.data.id] = node;
  }
  // BFS to get depths
  BFS(nodes[0], id2node, adjacencyList, reverseAdjacencyList, 4);

  

  return graphData;
  // return { nodes, edges: betterEdges };
};

const _deduplicateEdges = (edges: CytoLink[]) => {
  const edgeSet = new Set<string>();
  const dedupedEdges = [];
  for (let edge of edges) {
    const key = edge.data.source + edge.data.target;
    if (!edgeSet.has(key)) {
      edgeSet.add(key);
      dedupedEdges.push(edge);
    }
  }
  return dedupedEdges;
}

export const processDataForLayouting = (graphData: CytoData, collectLang: string, 
      pruningIterations: number, branchingIterations: number, 
      doTR: boolean) => {
  // recursively remove leaf nodes that are not the collect lang, to make the graph more readable

  const numCollectLang = graphData.nodes.filter(node => node.data.lang === collectLang).length;

  let result = graphData;
  if (numCollectLang > 0) {
    
    // const maxIterations = pruningIterations;
    let goodNodes: CytoNode[] = graphData.nodes.filter(node => !node.data.depth || node.data.depth <= branchingIterations);
    let goodEdges: CytoLink[] = _deduplicateEdges(graphData.edges);

    if ( pruningIterations === 0) {
      // to be safe, we still need to remove leaf nodes that are not the collect lang
      const oldGoodEdges = goodEdges;
      goodEdges = [];
      for (let edge of oldGoodEdges) {
        if (goodNodes.find(node => node.data.id === edge.data.source) 
          && goodNodes.find(node => node.data.id === edge.data.target)) {
          goodEdges.push(edge);
        }
      }
    }
    for (let i = 0; i < pruningIterations; i++) {
      // only keep nodes such that one of these are true:
      // 1. it's the root node
      // 2. it's the collect lang
      // 3. it is NOT a leaf node

      const nonLeafNodes = new Set<string>();
      const numIncoming: Record<string, number> = {};
      for (let edge of goodEdges) {
        nonLeafNodes.add(edge.data.source);
        numIncoming[edge.data.target] = (numIncoming[edge.data.target] || 0) + 1;
      }
      // leafNodes = leafNodes \ nonLeafNodes
      
      goodNodes = goodNodes.filter(node => {
        return node.data['root'] || node.data.lang === collectLang || nonLeafNodes.has(node.data.id) ||
          numIncoming[node.data.id] > 1;
      });
      // get corresponding edges
      const oldGoodEdges = goodEdges;
      goodEdges = [];
      for (let edge of oldGoodEdges) {
        if (goodNodes.find(node => node.data.id === edge.data.source) 
          && goodNodes.find(node => node.data.id === edge.data.target)) {
          goodEdges.push(edge);
        }
      }
      // console.log('Iteration', i, numIncoming);


    }

    
    result = { nodes: goodNodes, edges: goodEdges };
  }

  // transitive reduction
  if(doTR) {
    const { adjacencyList, reverseAdjacencyList } = generateAdjacencyList(result);

    const id2node = {} as Record<string, CytoNode>;
    for (let node of result.nodes) {
      id2node[node.data.id] = node;
    }
    const betterAdjList = transitive_reduction(id2node, adjacencyList, reverseAdjacencyList);

    const betterEdges = [];
    for (let source in betterAdjList) {
      for (let target of betterAdjList[source]) {
        betterEdges.push({
          data: {
            source,
            target,
          }
        });
      }
    }
    result = { nodes: result.nodes, edges: betterEdges };
  }
  return result;
  
}