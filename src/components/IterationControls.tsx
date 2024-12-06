import { Input } from "@/components/ui/input";

type IterationControlsProps = {
  branchingIterations: number;
  setBranchingIterations: (n: number) => void;
  pruningIterations: number;
  setPruningIterations: (n: number) => void;
};

export const IterationControls = ({
  branchingIterations,
  setBranchingIterations,
  pruningIterations,
  setPruningIterations
}: IterationControlsProps) => {
  return (
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
          max="5"
          value={pruningIterations}
          onChange={(e) => setPruningIterations(Number(e.target.value))}
        />
      </div>
    </div>
  );
};