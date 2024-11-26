import json
import os
import glob
# from tqdm import tqdm

# Directory containing the input .jsonl files
input_dir = "sorted/"
# Directory to save the sorted .jsonl files

# Get a list of all .jsonl files in the input directory
files = glob.glob(os.path.join(input_dir, "etytree_*.jsonl"))

output_log = "problematic.txt"
for i, file in enumerate(files):
    # Extract the subpart from the filename
    subpart = os.path.basename(file).split('_')[1].split('.')[0]
    
    if '_' in subpart:
        continue
    subpart = int(subpart)
    if subpart < 90:
        continue
    
    with open(file, 'r') as f_in:
        for line in f_in:
            # Parse the JSON line
            data = json.loads(line)

            word = data.get("word")
            lang = data.get("lang")
            
            has_substr = False
            for val in data.get("etymology_templates", []):
                if "str left" == val['name'] or "str right" == val['name']:
                    has_substr = True
                    break
            has_lite = False
            for val in data.get("etymology_templates", []):
                if "lite" in val['name']:
                    has_lite = True
                    break
            # print(f"{word}\t{lang}\t{has_substr}\t{has_lite}")
            # if has_substr and has_lite:
            with open(output_log, 'a', encoding='utf-8') as f_out:
                f_out.write(f"{word}\t{lang}\t{has_substr}\t{has_lite}\n")
