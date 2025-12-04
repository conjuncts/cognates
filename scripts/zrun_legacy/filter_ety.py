import os
import json
from tqdm import tqdm

# Directory containing the input .jsonl files
input_dir = 'D:/etytreealg/chunked'

# Directory to write the filtered .jsonl files to
output_dir = 'C:/myrriad/etytreealg/ety'

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Iterate over the files in the input directory
for filename in tqdm(os.listdir(input_dir)):
    if filename.endswith('.jsonl'):
        # Open the input file and the corresponding output file
        with open(os.path.join(input_dir, filename), 'r') as infile, \
             open(os.path.join(output_dir, filename), 'w') as outfile:

            # Iterate over the lines (JSON objects) in the input file
            for line in infile:
                obj = json.loads(line)

                # If the object meets the conditions, write it to the output file
                if ('etymology_text' in obj and obj['etymology_text']) or \
                   ('etymology_templates' in obj and obj['etymology_templates']):
                    outfile.write(json.dumps(obj) + '\n')