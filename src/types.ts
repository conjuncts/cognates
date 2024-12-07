export type APINode = [number, string, string]; // v_id, word, lang
export type APIEdge = [number, number, boolean]; // e_id, n_id, is_p
export type APIResponse = {
  vertices: APINode[];
  edges: APIEdge[];
};

export type CytoNode = {
  data: {
    id: string;
    label: string;
    word: string;
    lang: string;
    root?: boolean;
    depth?: number;
  }
};

export type CytoLink = {
  data: {
    source: string;
    target: string;
  }
};

export type CytoData = {
  nodes: CytoNode[];
  edges: CytoLink[];
};