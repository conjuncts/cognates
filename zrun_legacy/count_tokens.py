# count tokens in ./sorted
import tiktoken
import os
import glob
from tqdm import tqdm
import json

# Directory containing the input .jsonl files
input_dir = "sorted/"
# Directory to save the sorted .jsonl files

# Get a list of all .jsonl files in the input directory
files = list(glob.glob(os.path.join(input_dir, "etytree_*.jsonl")))
total_tokens = 0
total_n = 0
tknr = tiktoken.get_encoding("cl100k_base")

# encountered_templates = {}
subpart_to_tokens = {}
for i, file in tqdm(enumerate(files)):
    
    with open(file, 'r') as f_in:
        for line in f_in:
            # Parse the JSON line
            data = json.loads(line)

            # only focus on words >5 templates
            # if len(data["etymology_templates"]) < 4:
                # continue
            ety = data.get("etymology_text", "")
            
            tokens = tknr.encode(ety)
            total_tokens += len(tokens)
            total_n += 1
            
            # for template in data["etymology_templates"]:
            #     name = template["name"]
            #     if name not in encountered_templates:
            #         encountered_templates[name] = 0
            #     encountered_templates[name] += 1
            # subpart = data["subpart"]
            
            subpart = len(data.get("etymology_templates", []))
            if subpart not in subpart_to_tokens:
                subpart_to_tokens[subpart] = 0
            subpart_to_tokens[subpart] += len(tokens)
            

print(f"{total_tokens} tokens, n={total_n} (GPT4: ${total_tokens * 10 / 1E6}) (GPT3.5: ${total_tokens * 0.5 / 1E6})")

# sort encountered_tokens by key, ascending
subpart_to_tokens = {k: v for k, v in sorted(subpart_to_tokens.items(), key=lambda item: item[1], reverse=True)}
with open("encountered_tokens.json", "w") as f:
    json.dump(subpart_to_tokens, f)
# cost (gpt4): 