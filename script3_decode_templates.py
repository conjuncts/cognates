import os
import polars as pl
import json
from tqdm import tqdm

from etytreealg.decode import langcodes as langcodes


def load_df():
    df_dest = 'data/parquet/ety_expanded.parquet'
    return pl.read_parquet(df_dest)

def hydrate_df(df):
    """
    Call json.loads on the columns that are stored as JSON strings
    which are templates, related, and descendants
    """

    # note that Object datatype cannot be written to parquet/arrow
    df = df.with_columns([
        pl.col('templates').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('templates_h'),
        pl.col('related').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('related_h'),
        pl.col('descendants').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('descendants_h'),
    ])

    df = df.drop(['templates', 'related', 'descendants'])

    print("Hydrated!")
    return df

# Save the hydrated column separately
# DOESN'T WORK
# def save_hydrated_column(df: pl.DataFrame, col_name: str, pickle_path: str):
#     import pickle as pkl
#     # Assuming df already has the templates_h column computed
#     templates_h_series = df[col_name].to_pandas()
#     with open(pickle_path, 'wb') as f:
#         pkl.dump(templates_h_series, f)

# def load_hydrated_column(pickle_path: str):
#     import pickle as pkl
#     with open(pickle_path, 'rb') as f:
#         templates_h_series = pkl.load(f)
#     return pl.from_pandas(templates_h_series)


# def hydrate_templates(df):
#     t_column = []
#     for templates_str in tqdm(df['templates']):
#         templates = json.loads(templates_str) if templates_str else []
#         t_column.append(templates)
#     return t_column

def template_frequencies(df, t_column=None):
    """
    get frequencies of each template
    """
    template_frequencies = {}
    # for templates_str in tqdm(df['templates_h']):
        # templates = json.loads(templates_str) if templates_str else []
        # templates = templates_str if templates_str else []
    
    # for templates in t_column:

    for templates in df['templates_h']:
        if not templates:
            continue
        for template in templates:
            # collect frequencies based on template['name']
            if template['name'] not in template_frequencies:
                template_frequencies[template['name']] = 0
            template_frequencies[template['name']] += 1

    # sort template_frequncies by frequency
    sorted_template_frequencies = sorted(template_frequencies.items(), key=lambda x: x[1], reverse=True)
    return sorted_template_frequencies

from etytreealg.graph.graph_io import collate_templates

def lang_sr_by_template_arg(template_examples):
    """
    get empirical rate that a template argument is a langcode
    """
    sr_by_arg = {} # success rate by key
    for template in template_examples:
        for key, value in template.items():
            if key not in sr_by_arg:
                sr_by_arg[key] = {'success': 0, 'total': 0}
            if value:
                sr_by_arg[key]['total'] += 1
                if langcodes.is_langcode(value):
                    sr_by_arg[key]['success'] += 1
    return sr_by_arg

def predicted_lang_keys_per_template(lang_success_rates, debug=False):
    """
    Empirically determine which arguments are likely to be lang codes in a given template.
    Does this based on the success rate of a key being a lang code.
    Returns a dictionary of template: str -> set[str]

    Criteria for being a suspected lang key
    1. key contains 'lang' OR
    2. success rate > 95% AND total > 5

    If debug is True, then we also return the warning keys, where the success rate is between 0.8 and 0.95.

    We have exceptions: 

    1. Han compound's 'ls' is one of ['i', 'ic', 'psc'] but do NOT represent langcodes
    2. Same for liushu: ['p', 'i', 'ic', 'psc']

    4. surface analysis & surf 1 can be a lang, but surf 1 can also be a reference to another template
    (like +suf)
    5. noncog contains a large frequency of language families, due to its migration from {{etyl}}
    6. Hira-dakuten 2 is actually Hepburn romanization of the character, which happens to be a lot of used 2- or 3- letter codes
    7. Kana-dakuten: same
    8. wp & zh-wp's argument is technically a lang code, but not the exact same one https://en.wiktionary.org/wiki/Template:wikipedia
    9. cog 1 may be a comma-separated list of langcodes. The same is true of bor 2, bor+ 2, 
    (1 instance only:) clq 2, cal 2, ubor 2, ncog 1,
    10. dercat may have "<" in fields normally occupied by a language.
    11. inc-ext looks confusing
    12. pi-root 1 and tl-bay sc are NOT languages

    """
    suspected_lang_keys_per_template = {}
    _warning_keys = {}
    for template, sr in lang_success_rates.items():
        # criteria for being a suspected lang key
        # 1. key contains 'lang' OR
        # 2. success rate > 95% AND total > 5
        suspected_lang_keys = {k for k, v in sr.items() if 'lang' in k or v['total'] and v['total'] >= 5 and v['success'] / v['total'] >= 0.95}
        
        # check for those between 0.8 and 0.95 and print them as a warning: usually, 
        for k, v in sr.items():
            if v['total'] and v['total'] >= 5 and 0.5 <= v['success'] / v['total'] < .9999:
                # print(f"WARNING: {template} {k} {v['success'] / v['total']:.2%}")
                _warning_keys[(template, k)] = v['success'] / v['total']
        
        suspected_lang_keys_per_template[template] = list(suspected_lang_keys)
    if debug:
        return suspected_lang_keys_per_template, _warning_keys
    return suspected_lang_keys_per_template

def predicted_word_keys_per_template(word_success_rates, debug=False):
    """
    Criteria for being a WORD

    1. filter to only allow keys that are strictly numerical
    2. preference is given to the most common key
    3. preference is given to the key, strictly numerical, with the lowest value

    4. require that key has success rate > 30%
    5. preference is given if key has success rate > 80%
    """
    predicted_word_keys = {}
    nonlexical = set()

    def sr(v):
        return v['success'] / v['total'] if v['total'] else 0
    for template, srs_full in word_success_rates.items():
        # criteria for being a suspected lang key
        # 1. key contains 'lang' OR
        # 2. success rate > 95% AND total > 5
        suspected = set()
        
        success_rates = {k: v for k, v in srs_full.items() if k.isnumeric()}

        if not success_rates:
            predicted_word_keys[template] = []
            continue
        lowest_k = min(success_rates, key=lambda x: int(x))
        most_freq_k = max(success_rates, key=lambda x: success_rates[x]['total'])

        # give preference to these candidates
        if sr(success_rates[lowest_k]) > 0.3:
            suspected.add(lowest_k)
        if sr(success_rates[most_freq_k]) > 0.3:
            suspected.add(most_freq_k)

        # for the non-preferential, check for those between 0.3 and 0.8
        for k, v in success_rates.items():
            if sr(v) > 0.7:
                suspected.add(k)
                # print(f"WARNING: {template} {k} {v['success'] / v['total']:.2%}")
                pass
        
        if not suspected:
            # there are numerical keys, but none of them are words.
            # this is unusual, and should be noted
            nonlexical.add(template)
            

        
        predicted_word_keys[template] = sorted(suspected, key=lambda x: int(x))
    if debug:
        return predicted_word_keys, nonlexical
    return predicted_word_keys

def word_sr_by_template_arg(template_examples: list[dict[str, str]], known_lang_keys: list[str], all_words_set: pl.Series):
    """
    get empirical rate that a template argument is a word

    criteria for being a suspected word key:
    1. key is not a known LANG key
    
    metrics:
    1. word success rate: the value is present in all_words_set
    2. nonlatin rate: the value has at least one non-latin character
    3. unique rate: number of unique values. If there are very few unique words (ie. enum), then it's probably not a WORD.


    """
    sr_by_arg = {} # word success rate by key
    for example in template_examples:
        for key, value in example.items():
            if key in known_lang_keys:
                continue
            if key not in sr_by_arg:
                sr_by_arg[key] = {'total': 0, 'success': 0, 'nonlatin': 0, 'unique': set()}
            if value:
                # allow reconstructions to work
                if value.startswith('*'):
                    value = value[1:]
                sr_by_arg[key]['total'] += 1
                if value in all_words_set:
                    sr_by_arg[key]['success'] += 1
                if not value.isascii():
                    sr_by_arg[key]['nonlatin'] += 1
                sr_by_arg[key]['unique'].add(value)

    for key, v in sr_by_arg.items():
        v['unique'] = len(v['unique'])
                
    return sr_by_arg

if __name__ == '__main__':
    df = load_df()
    df = df.with_row_index("index")

    print("Loaded!")

    # t_column = hydrate_templates(df) # 33 seconds
    import time
    start = time.time()
    df = hydrate_df(df)
    end = time.time()
    print(f"Hydrated in {end - start} seconds")

    # head = df.head(1000)


    # result 1: template frequencies
    write_dest = 'data/templates/template_freqs.json'
    if not os.path.exists(write_dest):
        sorted_template_frequencies = template_frequencies(df)
        with open(write_dest, 'w') as f:
            json.dump(sorted_template_frequencies, f)
    else:
        with open(write_dest, 'r') as f:
            sorted_template_frequencies = json.load(f)

    print(sorted_template_frequencies[:10])

    # result 2: success rates of langcodes by template argument
    desired_templates = [template for template, freq in sorted_template_frequencies if freq >= 20]
    collated_templates = collate_templates(df, desired_templates)
    write_dest = 'data/templates/template_langcode_sr.json'
    if not os.path.exists(write_dest):


        lang_success_rates = {tname: lang_sr_by_template_arg(t_examples) for tname, t_examples in collated_templates.items()}

        # write success_rates to file
        with open('data/templates/template_langcode_sr.json', 'w') as f:
            json.dump(lang_success_rates, f)
    else:
        with open(write_dest, 'r') as f:
            lang_success_rates = json.load(f)
    
    # result 3: predicted lang keys
    write_dest = 'data/templates/predicted_lang_keys.json'
    if not os.path.exists(write_dest):
        predicted_lang_keys, _warning_keys = predicted_lang_keys_per_template(lang_success_rates, debug=True)
        with open(write_dest, 'w') as f:
            json.dump(predicted_lang_keys, f)
    else:
        with open(write_dest, 'r') as f:
            predicted_lang_keys = json.load(f)

    
    # result 4: word success rates
    write_dest = 'data/templates/word_sr.json'
    if not os.path.exists(write_dest):

        all_words_set = set(df['word'].unique())
        word_success_rates = {}
        for tname, t_examples in tqdm(collated_templates.items()):
            suspected_lang_keys = predicted_lang_keys.get(tname, [])
            word_success_rates[tname] = word_sr_by_template_arg(t_examples, suspected_lang_keys, all_words_set)
    
        with open(write_dest, 'w') as f:
            json.dump(word_success_rates, f)
    else:
        with open(write_dest, 'r') as f:
            word_success_rates = json.load(f)
    
    # result 5: predicted word keys
    predicted_word_keys, nonlexical = predicted_word_keys_per_template(word_success_rates, debug=True)
    # exceptions
    predicted_word_keys['adverbial accusative'] = ['2']
    predicted_word_keys['cardinalbox'] = ['5', '6']
    predicted_word_keys['initialism'] = ['2']

    with open('data/templates/predicted_word_keys.json', 'w') as f:
        json.dump(predicted_word_keys, f)

    # these templates take in multiple words
    multilexical = {k: v for k, v in predicted_word_keys.items() if len(v) > 1}

    # these templates take in arbitrarily many number of words
    n_lexical = set()
    for tname, keys in predicted_word_keys.items():
        if not keys:
            continue
        if max([int(k) for k in keys], default=0) >= 6: # if we have a key greater than '6', then it's probably an affix or smth
            n_lexical.add(tname)
        elif '5' in keys and all(key in keys for key in word_success_rates[tname]):
            # all numerical keys from 2-5 are indeed successful
            n_lexical.add(tname)
        
        

    # exceptions
    n_lexical.add('Han compound')
    n_lexical.add('suf')
    n_lexical.add('blend')
    n_lexical.add('pre')
    n_lexical.remove('cardinalbox')
    n_lexical.remove('vi-etym-sino')
    n_lexical.remove('t2i-Egyd')



