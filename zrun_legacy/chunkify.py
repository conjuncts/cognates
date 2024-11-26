import json
import os

def read_large_file(file_path):
    with open(file_path, encoding='utf-8') as file:
        for line in file:
            yield json.loads(line)

def write_to_file(data, output_path, file_number):
    with open(os.path.join(output_path, f'output_{file_number}.jsonl'), 'w') as file:
        for item in data:
            file.write(json.dumps(item))
            file.write('\n')

def process_large_file(input_path, output_path):
    data_buffer = []
    file_number = 1
    for item in read_large_file(input_path):
        data_buffer.append(item)
        if len(data_buffer) == 1000:
            write_to_file(data_buffer, output_path, file_number)
            data_buffer = []
            file_number += 1
    if data_buffer:
        # Write the last set of lines that are less than 1000
        write_to_file(data_buffer, output_path, file_number)

# Call the function with your paths
process_large_file('raw-wiktextract-data.json', 'D:/etytreealg')
