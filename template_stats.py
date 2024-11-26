# sort encountered_templates.json in descending order of value
import json
with open("encountered_templates.json", "r") as f:
    encountered_templates = json.load(f)
encountered_templates = {k: v for k, v in sorted(encountered_templates.items(), key=lambda item: item[1], reverse=True)}
with open("encountered_templates_sorted.json", "w") as f:
    json.dump(encountered_templates, f)