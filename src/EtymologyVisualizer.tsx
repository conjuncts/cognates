import { useCallback, useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChevronsRight, Loader2, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

cytoscape.use(dagre);

const apiRoot = import.meta.env.DEV ? '/api' : 'https://aukwjgzbqtsbvrhzyisi.supabase.co'; // '/api'

const langnames = {
  'es': 'Spanish',
  'pt': 'Portuguese',
  'fr': 'French',
  'it': 'Italian',
  'en': 'English',
  'la': 'Latin',
  'osp': 'Old Spanish',
  'fro': 'Old French',
  'grc': 'Ancient Greek',
  'ine-pro': 'Proto-Indo-European',
  'itc-pro': 'Proto-Italic'
} as Record<string, string>;

const EtymologyVisualizer = () => {
  type APINode = [number, string, string]; // v_id, word, lang
  type APIEdge = [number, number, boolean]; // e_id, n_id, is_p
  type APIResponse = {
    vertices: APINode[];
    edges: APIEdge[];
  };

  type CytoNode = {
    data: {
      id: string;
      label: string;
      word: string;
      lang: string;
      root?: boolean;
    }
  };
  type CytoLink = {
    data: {
      source: string;
      target: string;
    }
  };
  type CytoData = {
    nodes: CytoNode[];
    edges: CytoLink[];
  }

  const [word, setWord] = useState('');
  const [lang, setLang] = useState('es');
  const [collectLang, setCollectLang] = useState('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [graphData, setGraphData] = useState<CytoData>({ nodes: [], edges: [] });

  const [branchingIterations, setBranchingIterations] = useState(2);
  const [pruningIterations, setPruningIterations] = useState(1);
  const cyRef = useRef<cytoscape.Core | null>(null);

  // const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [wiktionaryUrl, setWiktionaryUrl] = useState<string | null>(null);
  // const [wiktionaryLangname, setWiktionaryLangname] = useState<string | null>(null);
  const [isWiktVisible, setIsWiktVisible] = useState(true);

  const [wiktLoading, setWiktLoading] = useState(false);


  const handleIframeLoad = () => {
    setWiktLoading(false);

    // if (iframeRef.current && wiktionaryLangname) {
    //   // iframeRef.current.src = url;
    //   iframeRef.current.contentWindow!.location.hash = wiktionaryLangname;
    // }
    
  };


  // desired format:
//   {
//     nodes: [
//         { data: { id: '184970', label: 'gozar (es)' } },
//         { data: { id: '780935', label: 'gaudium (la)' } }
//     ],
//     edges: [
//         { data: { source: '417154', target: '184970', directed: true } },
//         { data: { source: '780935', target: '574779', directed: true } }
//     ]
// };
  const processDataForGraph = (apiData: APIResponse) => {
    const nodes = apiData.vertices.map((node, i) => ({
      data: {
        id: String(node[0]),
        // label: `${node[1]} (${langnames[node[2]] || node[2]})`,
        label: `${node[1]} (${node[2]})`,
        word: node[1],
        lang: node[2],
        root: i === 0,
      }
    }));


    // const edges = apiData.edges.map(edge => ({
    //   data: {
    //     source: String(edge[2] ? edge[0] : edge[1]),
    //     target: String(edge[2] ? edge[1] : edge[0]),
    //   }
    // }));

    // deduplicate edges
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
  const processDataForLayouting = (graphData: CytoData, pruningIterations: number) => {
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

  const fetchEtymology = async () => {
    setLoading(true);
    setError('');
    try {
      let data;
      if(word === 'gozar' && lang === 'es') {
        // cache
        data = {"vertices":[[184970,"gozar","es"],[417154,"-ar","es"],[574779,"gozo","es"],[763087,"gozar","osp"],[718139,"gozar","pt"],[780935,"gaudium","la"],[1070506,"joie","fr"],[502740,"gozo","pt"],[1078561,"jo","en"],[515791,"gaudimonium","la"],[248533,"Gaudium","de"],[393575,"gaudio","it"],[232120,"goivo","pt"],[347415,"gaudialis","la"],[137060,"gaudy","en"],[172337,"joy","en"],[110014,"jewel","en"],[539781,"-ium","la"],[328297,"gaudeo","la"],[6839,"joie","fro"],[933425,"goujat","fr"],[1063510,"gau","la"],[36119,"ioye","frm"],[1008269,"Gaius","la"],[480526,"gaudivigens","la"],[1015593,"gáudio","pt"],[439742,"gavisurus","la"],[980616,"Gayo","es"],[178323,"gayo","es"],[710026,"praegaudeo","la"],[1047639,"aggaudeo","la"],[1066507,"jouir","fr"],[184045,"geh₂w-","ine-pro"],[989384,"Gavius","la"],[652902,"congaudeo","la"],[1026299,"godere","it"],[924220,"gaudere","it"],[419846,"gaudente","it"],[859062,"Caius","la"],[117301,"γάνος","grc"],[785740,"geh₂widéh₁yeti","ine-pro"],[842743,"jolly","en"],[907917,"γάνῡμαι","grc"],[1071027,"vigeo","la"],[942307,"Caio","pt"],[850982,"γαίω","grc"],[229953,"Γάϊος","grc"],[180619,"Κάϊος","grc"],[824631,"Cnaeus","la"],[61895,"jolif","fro"],[894639,"supergaudeo","la"],[1035438,"gaudens","la"],[35057,"gaudibundus","la"],[537502,"-alis","la"],[380370,"gavisus","la"],[555572,"Caio","it"],[321762,"Ɔ","la"],[538435,"Gaipor","la"],[1025791,"joir","fro"],[278475,"-monium","la"],[1044986,"Gaia","la"],[356362,"gaudir","fr"],[300926,"pergaudeo","la"],[1046519,"γαῦρος","grc"],[489658,"gaius","la"],[458885,"gaudebundus","la"],[287041,"geai","fr"],[1048231,"gāwidēō","itc-pro"]],"edges":[[417154,184970,true],[574779,184970,true],[763087,184970,true],[718139,763087,false],[780935,574779,true],[780935,574779,true],[1070506,780935,false],[502740,780935,false],[1078561,780935,false],[515791,780935,false],[248533,780935,false],[393575,780935,false],[248533,780935,false],[232120,780935,false],[347415,780935,false],[137060,780935,false],[137060,780935,false],[172337,780935,false],[110014,780935,false],[539781,780935,true],[328297,780935,true],[328297,780935,false],[718139,780935,false],[6839,780935,false],[933425,780935,false],[1063510,780935,false],[110014,780935,false],[36119,780935,false],[1008269,780935,false],[480526,780935,false],[1015593,780935,false],[933425,780935,false],[439742,328297,false],[980616,1008269,false],[178323,1008269,false],[980616,1008269,false],[710026,328297,false],[1008269,328297,true],[1047639,328297,false],[1066507,328297,false],[184045,328297,true],[989384,1008269,false],[652902,328297,false],[1026299,328297,false],[924220,328297,false],[1026299,328297,false],[419846,328297,false],[859062,1008269,false],[117301,328297,true],[785740,328297,true],[842743,328297,false],[907917,328297,true],[1071027,480526,true],[942307,1008269,false],[850982,328297,true],[229953,1008269,false],[180619,1008269,false],[989384,1008269,true],[1008269,328297,false],[824631,1008269,false],[842743,328297,false],[61895,328297,false],[894639,328297,false],[1035438,328297,false],[184045,1008269,true],[35057,328297,false],[537502,347415,true],[380370,328297,false],[555572,1008269,false],[419846,328297,false],[321762,1008269,false],[538435,1008269,false],[1025791,328297,false],[278475,515791,true],[1044986,1008269,false],[356362,328297,false],[356362,328297,false],[300926,328297,false],[842743,328297,false],[1046519,328297,true],[489658,1008269,false],[458885,328297,false],[287041,1008269,false],[842743,328297,false],[1048231,328297,true]]};
      } else {
        const response = await fetch(apiRoot + '/functions/v1/serve-deep', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF1a3dqZ3picXRzYnZyaHp5aXNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI5OTE1MzMsImV4cCI6MjA0ODU2NzUzM30.HashNMzUEZYlvHvlW7iwV4zeuarh4Yy5kAtKgF-WSOI',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ word, lang, n: branchingIterations }),
        });

        data = await response.json();
      }
      const processed = processDataForGraph(data);
      setGraphData(processed);
    } catch (err) {
      setError('Failed to fetch etymology data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const initializeCytoscape = useCallback(() => {
    if (!cyRef.current) {
      const processed = processDataForLayouting(graphData, pruningIterations);
      // console.log(processed);
      // cyRef.current.add([...graphData.nodes, ...graphData.edges]);

      cyRef.current = cytoscape({
        container: document.getElementById('cy'),
        elements: [...processed.nodes, ...processed.edges],
        style: [
          {
            selector: 'node',
            style: {
              'label': 'data(label)',
              'text-valign': 'center',
              'text-halign': 'center',
              // 'background-color': '#0074D9',
              'color': '#000000',
              'font-size': '12px',
              'shape': 'ellipse',
              'background-color': 'lightblue', // Default color
            }
          },
          {
            selector: 'node[lang = "en"]',
            style: {
                'background-color': 'lightgreen', // Nodes with "es" language
            }
          },
          {
            selector: 'node[?root]',
            style: {
                'background-color': 'red', // Node 0 specifically
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 2,
              'line-color': '#AAAAAA',
              'target-arrow-color': '#AAAAAA',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
            }
          }
        ],
        layout: {
          name: 'dagre',
          rankDir: 'TB',
        } as any
      });

      cyRef.current.on('tap', 'node', (event) => {
        const node = event.target;
        const word = node.data('word');
        const lang = node.data('lang');
        const langname = langnames[lang];
        let url;
        if(langname.includes('Proto')) {
          url = `https://en.wiktionary.org/wiki/Reconstruction:${langname}/${word}`;
        } else {
          url = `https://en.wiktionary.org/wiki/${word}#${langname}`;
        }

        setWiktionaryUrl(currentUrl => {
          if (url === currentUrl) return currentUrl;
          setWiktLoading(true);
          // setWiktionaryLangname(langname);
          return url;
        });
        

        // set timeout for 5000ms, after which wiktLoading is still true, show error
        // setTimeout(() => {
        //   if (wiktLoading) {
        //     setWiktLoading(false);
        //     console.log("Timeout loading Wiktionary page");
        //   }
        // }, 5000);

        // setNodeSelected([word, lang]);




      });
    } else {
      // Update elements if Cytoscape instance already exists
      cyRef.current.elements().remove();
      const processed = processDataForLayouting(graphData, pruningIterations);
      // cyRef.current.add([...graphData.nodes, ...graphData.edges]);
      cyRef.current.add([...processed.nodes, ...processed.edges]);
      cyRef.current.layout({ name: 'dagre', rankDir: 'TB' } as cytoscape.LayoutOptions).run();
    }
  }, [graphData, pruningIterations]);

  useEffect(() => {
    if (graphData.nodes.length > 0) {
      initializeCytoscape();
    }
  }, [graphData, pruningIterations, initializeCytoscape]);

  

  return (
    
    <div className="flex flex-row w-full justify-center mt-6">
      
      <Card className="w-2/3 max-w-4xl"> 
        <CardHeader>
          
          <CardTitle>Network Graph</CardTitle>
        </CardHeader>
        <CardContent>
          <form
          onSubmit={(e) => {
            e.preventDefault();
            fetchEtymology();
          }}
          className="flex gap-4 mb-2"
          >
            <Input
              placeholder="Enter a word..."
              value={word}
              onChange={(e) => setWord(e.target.value)}
              className="flex-1"
            />
            <Select value={lang} onValueChange={setLang}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem className="cursor-pointer" value="es">Spanish</SelectItem>
                <SelectItem className="cursor-pointer" value="pt">Portuguese</SelectItem>
                <SelectItem className="cursor-pointer" value="fr">French</SelectItem>
                <SelectItem className="cursor-pointer" value="it">Italian</SelectItem>
              </SelectContent>
            </Select>
            <span className="self-center">→</span>
            <Select value={collectLang} onValueChange={setCollectLang}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Collect Language" />
              </SelectTrigger>
              <SelectContent className="cursor-pointer">
                <SelectItem value="en">English</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={fetchEtymology} disabled={loading || !word} type="submit">
              {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading
              </>
              ) : 'Search'}
            </Button>
          </form>

          <div className="flex gap-4 mb-6">
            <div className="flex flex-row items-center">
              <label htmlFor="branching" className="ml-2 mr-1 text-sm font-medium whitespace-nowrap">
                Depth=
              </label>
              <Input
                className="w-14"
                id="branching"
                type="number"
                min="1"
                // defaultValue="2"
                max="4"
                value={branchingIterations}
                onChange={(e) => setBranchingIterations(Number(e.target.value))}
              />
            </div>
            <div className="flex flex-row items-center">
              <label htmlFor="pruning" className="mr-1 text-sm font-medium whitespace-nowrap">
                Pruning N=
              </label>
              <Input
                className="w-14"
                id="pruning"
                type="number"
                min="0"
                // defaultValue="1"
                max="5"
                value={pruningIterations}
                onChange={(e) => setPruningIterations(Number(e.target.value))}
              />
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div id="cy" className="h-96 w-full border rounded-lg" />
        </CardContent>
      </Card>


      {isWiktVisible ? (
        <Card className="w-1/3 ml-2 flex flex-col relative">
          <CardHeader className="pb-2">
            <div className="flex justify-between items-center">
              <CardTitle>Wiktionary</CardTitle>
              {/* <span> {wiktionaryUrl} </span> */}
              <Button 
                variant="ghost" 
                size="icon"
                className="h-8 w-8 absolute top-4 right-4"
                onClick={() => setIsWiktVisible(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-grow pt-2">
            {wiktLoading && (
              // absolute inset-0 
              <div className="flex items-center justify-center bg-background/80 z-10">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            )}
            {wiktionaryUrl ? (
              <div className={ `h-full ${wiktLoading ? 'invisible' : ''}` }>
                <iframe
                  src={wiktionaryUrl}
                  // ref={iframeRef}
                  // className={ `w-full h-full border rounded-lg ${wiktLoading ? 'hidden' : ''}` }
                  className={ `w-full h-full border rounded-lg` }
                  title="Wiktionary Viewer"
                  onLoad={handleIframeLoad}
                  
                />
              </div>
            ) : (
              <p className="text-sm text-gray-500">Select a node to view its Wiktionary page.</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <Button
          variant="outline"
          size="icon"
          className="ml-2 h-8 self-center"
          onClick={() => setIsWiktVisible(true)}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      )}
      
    </div>
  );
};

export default EtymologyVisualizer;
