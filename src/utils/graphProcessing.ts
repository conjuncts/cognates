import { CytoData, APIResponse, CytoNode, CytoLink } from '../types';

export const processDataForGraph = (apiData: APIResponse): CytoData => {
  const nodes = apiData.vertices.map((node, i) => ({
    data: {
      id: String(node[0]),
      label: `${node[1]} (${node[2]})`,
      word: node[1],
      lang: node[2],
      root: i === 0,
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

  return { nodes, edges };
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

export const processDataForLayouting = (graphData: CytoData, collectLang: string, pruningIterations: number) => {
    // recursively remove leaf nodes that are not the collect lang, to make the graph more readable

    const numCollectLang = graphData.nodes.filter(node => node.data.lang === collectLang).length;
    if (numCollectLang > 0) {
      
      // const maxIterations = pruningIterations;
      let goodNodes: CytoNode[] = graphData.nodes;
      let goodEdges: CytoLink[] = _deduplicateEdges(graphData.edges);
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

      
      return { nodes: goodNodes, edges: goodEdges };
    }
    return graphData;
  }