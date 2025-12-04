import json
import os
import glob
from tqdm import tqdm

# Directory containing the input .jsonl files
input_dir = "ety/"
# Directory to save the sorted .jsonl files
output_dir = "sorted/"

# Get a list of all .jsonl files in the input directory
files = glob.glob(os.path.join(input_dir, "output_*.jsonl"))

good = 0
total = 0
for i, file in tqdm(enumerate(files)):
    # Extract the subpart from the filename
    subpart = os.path.basename(file).split('_')[1].split('.')[0]
    
    
    with open(file, 'r') as f_in:
        for line in f_in:
            total += 1
            # Parse the JSON line
            data = json.loads(line)

            # Check the length of "etymology_templates"
            # obtain templates
            templates = data.get("etymology_templates", [])
            
            # if there is a "-lite" template, skip (because of bug with substring)
            if any(["-lite" in template["name"] for template in templates]):
                continue
            good += 1
            
            # filter out any bad templates
            # exclusions = ["str left", "str_index-lite", "str len", "str_index-lite/logic", "str right", "str_index", "str_index/logic"]
            # if it starts with "str " or "str_", exclude it
            
            # exclusions = ["str ", "str_"]
            # templates = [template for template in templates if not any([template["name"].startswith(exclusion) for exclusion in exclusions])]
            # data["etymology_templates"] = templates
            

            
            
            length = len(data.get("etymology_templates", []))
            if length >= 2:
                # Add the "subpart" field to the JSON
                data["subpart"] = subpart

                
                if length == 2:
                    name = f"etytree_2_{i // 1000}.jsonl"
                elif length == 3:
                    name = f"etytree_3_{i // 1000}.jsonl"
                elif length > 100:
                    name = f"etytree_100.jsonl"
                else:
                    name = f"etytree_{length}.jsonl"
                # Write the modified JSON line to the output file
                with open(os.path.join(output_dir, name), 'a') as f_out:
                    f_out.write(json.dumps(data) + '\n')
print(good, total, good / total)