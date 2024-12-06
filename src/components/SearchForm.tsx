import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

type SearchFormProps = {
  word: string;
  setWord: (word: string) => void;
  lang: string;
  setLang: (lang: string) => void;
  collectLang: string;
  setCollectLang: (lang: string) => void;
  loading: boolean;
  onSubmit: () => void;
};

export const SearchForm = ({
  word, setWord, lang, setLang, collectLang, setCollectLang, loading, onSubmit
}: SearchFormProps) => {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
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
          <SelectItem className="cursor-pointer" value="de">German</SelectItem>
          <SelectItem className="cursor-pointer" value="nl">Dutch</SelectItem>
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
      <Button onClick={onSubmit} disabled={loading || !word} type="submit">
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Loading
          </>
        ) : 'Search'}
      </Button>
    </form>
  );
};