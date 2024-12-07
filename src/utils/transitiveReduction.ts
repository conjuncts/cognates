import { CytoNode } from "@/types";

/**
 * Performs transitive reduction on a directed graph using a combination of
 * strongly connected component detection and DAG reduction.
 * 
 * @param id2node Dictionary mapping node IDs to CytoNodes
 * @param adjacencyList Forward adjacency list (u -> v means edge from u to v)
 * @param reverseAdjacencyList Reverse adjacency list (u -> v means edge from v to u)
 * @returns A new adjacency list containing only the edges in the transitive reduction
 */
export function transitive_reduction(
  id2node: Record<string, CytoNode>,
  adjacencyList: Record<string, string[]>,
  reverseAdjacencyList: Record<string, string[]>
): Record<string, string[]> {
  // Helper function for DFS
  function dfs(
    node: string,
    visited: Set<string>,
    finishOrder: string[],
    graph: Record<string, string[]>
  ) {
    if (visited.has(node)) return;
    visited.add(node);
    
    const neighbors = graph[node] || [];
    for (const neighbor of neighbors) {
      dfs(neighbor, visited, finishOrder, graph);
    }
    
    finishOrder.push(node);
  }

  // First pass of Kosaraju's algorithm - get finish times
  const visited = new Set<string>();
  const finishOrder: string[] = [];
  
  for (const nodeId in id2node) {
    dfs(nodeId, visited, finishOrder, adjacencyList);
  }

  // Second pass - find SCCs
  const sccVisited = new Set<string>();
  const nodeToScc = new Map<string, string>();
  const sccMembers = new Map<string, Set<string>>();
  
  function assignSCC(node: string, sccId: string) {
    if (sccVisited.has(node)) return;
    sccVisited.add(node);
    nodeToScc.set(node, sccId);
    
    if (!sccMembers.has(sccId)) {
      sccMembers.set(sccId, new Set());
    }
    sccMembers.get(sccId)!.add(node);
    
    const neighbors = reverseAdjacencyList[node] || [];
    for (const neighbor of neighbors) {
      assignSCC(neighbor, sccId);
    }
  }

  // Process nodes in reverse finish order
  for (let i = finishOrder.length - 1; i >= 0; i--) {
    const node = finishOrder[i];
    if (!sccVisited.has(node)) {
      assignSCC(node, node); // Use first node of SCC as its ID
    }
  }

  // Create the condensed DAG and track original edges
  const sccAdjList = new Map<string, Set<string>>();
  // Map from (sccFrom, sccTo) to array of [originalFrom, originalTo] pairs
  const originalEdges = new Map<string, Array<[string, string]>>();
  
  for (const [node, neighbors] of Object.entries(adjacencyList)) {
    const sccFrom = nodeToScc.get(node)!;
    
    for (const neighbor of neighbors) {
      const sccTo = nodeToScc.get(neighbor)!;
      if (sccFrom !== sccTo) { // Only add edges between different SCCs
        if (!sccAdjList.has(sccFrom)) {
          sccAdjList.set(sccFrom, new Set());
        }
        sccAdjList.get(sccFrom)!.add(sccTo);
        
        // Track original edges
        const key = `${sccFrom},${sccTo}`;
        if (!originalEdges.has(key)) {
          originalEdges.set(key, []);
        }
        originalEdges.get(key)!.push([node, neighbor]);
      }
    }
  }

  // Get topological sort of the DAG
  function topologicalSort(): string[] {
    const visited = new Set<string>();
    const result: string[] = [];
    
    function visit(scc: string) {
      if (visited.has(scc)) return;
      visited.add(scc);
      
      const neighbors = sccAdjList.get(scc) || new Set();
      for (const neighbor of neighbors) {
        visit(neighbor);
      }
      
      result.unshift(scc);
    }
    
    for (const scc of sccAdjList.keys()) {
      visit(scc);
    }
    
    return result;
  }

  // Perform transitive reduction on the DAG
  const topoOrder = topologicalSort();
  const sccReachable = new Map<string, Set<string>>();
  
  // Initialize reachability sets
  for (const scc of topoOrder) {
    sccReachable.set(scc, new Set([scc]));
  }
  
  // Compute reachability
  for (const scc of topoOrder) {
    const neighbors = sccAdjList.get(scc) || new Set();
    for (const neighbor of neighbors) {
      const neighborReachable = sccReachable.get(neighbor)!;
      for (const reachableNode of neighborReachable) {
        sccReachable.get(scc)!.add(reachableNode);
      }
    }
  }

  // Create the reduced adjacency list
  const reducedAdjList: Record<string, string[]> = {};
  
  // First, add edges within SCCs (they're all needed)
  for (const [_, members] of sccMembers.entries()) {
    if (members.size > 1) {
      for (const member of members) {
        reducedAdjList[member] = [];
        const memberNeighbors = adjacencyList[member] || [];
        for (const neighbor of memberNeighbors) {
          if (members.has(neighbor)) {
            reducedAdjList[member].push(neighbor);
          }
        }
      }
    }
  }

  // Then add edges between SCCs
  for (const [scc, neighbors] of sccAdjList.entries()) {
    for (const neighbor of neighbors) {
      let keepEdge = true;
      
      // Check if there's an indirect path through another neighbor
      for (const otherNeighbor of neighbors) {
        if (otherNeighbor !== neighbor && 
            sccReachable.get(otherNeighbor)!.has(neighbor)) {
          keepEdge = false;
          break;
        }
      }
      
      if (keepEdge) {
        // Get original edges between these SCCs
        const key = `${scc},${neighbor}`;
        const edges = originalEdges.get(key)!;
        
        // Add all original edges between these SCCs
        for (const [fromNode, toNode] of edges) {
          if (!reducedAdjList[fromNode]) {
            reducedAdjList[fromNode] = [];
          }
          reducedAdjList[fromNode].push(toNode);
        }
      }
    }
  }

  // Ensure all nodes are present in the result
  for (const nodeId in id2node) {
    if (!reducedAdjList[nodeId]) {
      reducedAdjList[nodeId] = [];
    }
  }

  return reducedAdjList;
}