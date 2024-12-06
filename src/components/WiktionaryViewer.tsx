import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronsRight, Loader2, X } from "lucide-react";

type WiktionaryViewerProps = {
  isVisible: boolean;
  setIsVisible: (visible: boolean) => void;
  url: string | null;
  loading: boolean;
  onIframeLoad: () => void;
};

export const WiktionaryViewer = ({
  isVisible,
  setIsVisible,
  url,
  loading,
  onIframeLoad
}: WiktionaryViewerProps) => {
  if (!isVisible) {
    return (
      <Button
        variant="outline"
        size="icon"
        className="ml-2 h-8 self-center"
        onClick={() => setIsVisible(true)}
      >
        <ChevronsRight className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Card className="w-1/3 ml-2 flex flex-col relative">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle>Wiktionary</CardTitle>
          <Button 
            variant="ghost" 
            size="icon"
            className="h-8 w-8 absolute top-4 right-4"
            onClick={() => setIsVisible(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-grow pt-2">
        {loading && (
          <div className="flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        )}
        {url ? (
          <div className={`h-full ${loading ? 'invisible' : ''}`}>
            <iframe
              src={url}
              className="w-full h-full border rounded-lg"
              title="Wiktionary Viewer"
              onLoad={onIframeLoad}
            />
          </div>
        ) : (
          <p className="text-sm text-gray-500">Select a node to view its Wiktionary page.</p>
        )}
      </CardContent>
    </Card>
  );
};