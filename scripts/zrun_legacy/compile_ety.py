# count tokens in ./sorted
import tiktoken
import os
import glob
from tqdm import tqdm
import json
import pandas as pd

# Directory containing the input .jsonl files
input_dir = "sorted/"
# Directory to save the sorted .jsonl files

# Get a list of all .jsonl files in the input directory
files = list(glob.glob(os.path.join(input_dir, "etytree_*.jsonl")))

# encountered_templates = {}
print(len(files))
collected = []
for i, file in tqdm(enumerate(files)):
    subpart = file.split("_", 1)[1].split(".")[0]
    
    splits = subpart.split("_")
    num_templates = splits[0]
    if len(splits) > 1:
        split = splits[1]
    else:
        split = -1

    with open(file, 'r') as f_in:
        for line in f_in:
            
            # Parse the JSON line
            data = json.loads(line)

            # only focus on words >5 templates
            # if len(data["etymology_templates"]) < 4:
                # continue
            ety = data.get("etymology_text", "")
            templates = data.get("etymology_templates", [])
            word = data.get("word", "")
            lang = data.get("lang", "")
            etymology_number = data.get("etymology_number", 0)
            subpart = data.get("subpart", 0)
            
            to_push = (word, lang, ety, templates, etymology_number, num_templates, split, subpart)
            collected.append(to_push)

df = pd.DataFrame(collected, columns=["word", "lang", "ety", "templates", "etymology_number", "num_templates", "split", "subpart"])
df.to_csv("ety_data.csv", index=False)