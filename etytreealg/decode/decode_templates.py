import json

_predicted_lang_keys = None
_predicted_word_keys = None

root = '' # ../'

def get_predicted_lang_keys():
    global _predicted_lang_keys
    if _predicted_lang_keys is not None:
        return _predicted_lang_keys
    
    with open(f"{root}data/templates/predicted_lang_keys.json") as f:
        _predicted_lang_keys = json.load(f)
    return _predicted_lang_keys


def get_predicted_word_keys():
    global _predicted_word_keys
    if _predicted_word_keys is not None:
        return _predicted_word_keys
    with open(f"{root}data/templates/predicted_word_keys.json") as f:
        _predicted_word_keys = json.load(f)
        # overrides
        _predicted_word_keys['adverbial accusative'] = ['2']
        _predicted_word_keys['cardinalbox'] = ['5', '6']
        _predicted_word_keys['initialism'] = ['2']
    return _predicted_word_keys

_word_sr = None
def get_word_sr():
    global _word_sr
    if _word_sr is not None:
        return _word_sr
    
    with open(f"{root}data/templates/word_sr.json") as f:
        _word_sr = json.load(f)
    return _word_sr

_multilexical = None
def get_multilexical():
    """
    Multilexical is any template that takes in multiple words.
    """
    # these templates take in multiple words
    global _multilexical
    if _multilexical is not None:
        return _multilexical
    
    predicted_word_keys = get_predicted_word_keys()
    word_success_rates = get_word_sr()
    _multilexical = {k: v for k, v in predicted_word_keys.items() if len(v) > 1}
    return _multilexical

n_lexical = None
def get_n_lexical():
    """
    n_lexical is any template that takes in arbitrarily many number of words.
    """
    global n_lexical
    if n_lexical is not None:
        return n_lexical
    
    n_lexical = set()

    predicted_word_keys = get_predicted_word_keys()
    word_success_rates = get_word_sr()
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
    return n_lexical


def reinsert_affix_hyphen(tname, tkey, word, maximal_suffix=None):
    """
    Templates like suffix, prefix, confix allow the hyphen to be omitted. 
    This reinserts it, so that we are able to find affixes.
    """
    is_suffix = False
    is_prefix = False
    # print(tname, tkey, word)
    if tname in ['suffix', 'suf']:
        if tkey == '3':
            is_suffix = True
    elif tname in ['prefix', 'pre']:
        if tkey == '2':
            is_prefix = True
    elif tname in ['confix', 'con']:
        if tkey == '2':
            is_prefix = True
        else:
            assert maximal_suffix is not None
            if int(tkey) == maximal_suffix:
                is_suffix = True
    else:
        return word
    if is_prefix:
        return word + '-'
    elif is_suffix:
        if word.startswith('*'):
            return '*-' + word[1:]
                # wow this sucks
        return '-' + word
    return word
    

def get_langcodes_and_words(tname, targs, host_langcode, parse_nonnumeric=False):
    """
    Given a template, return the language codes and words.
    """
    # print("hi")

    lang_keys = get_predicted_lang_keys()
    word_keys = get_predicted_word_keys()
    n_lexical = get_n_lexical()

    # get languages
    langs = set()
    for lang_key in lang_keys.get(tname, []):
        if not parse_nonnumeric and not lang_key.isnumeric():
            continue

        if lang_key not in targs:
            continue

        lang = targs[lang_key]
        langs.add(lang)

    if len(langs) > 1:
        # pop the source language, if it's there
        langs.discard(host_langcode)
    langs = list(langs)

    # get words
    words = []

    if tname in n_lexical:
        # n lexical works differently: we just take all the words that are not langs
        lang_keys = set(lang_keys.get(tname, []))
        for key in targs:
            if key.isnumeric() and key not in lang_keys:

                # prefix, suffix just happen to be in n_lexical
                word = targs[key]
                word = reinsert_affix_hyphen(tname, key, word)
                words.append(word)
    else:

        # otherwise, only take the words that we say are word keys
        for word_key in word_keys.get(tname, []):

            if not parse_nonnumeric and not word_key.isnumeric():
                continue

            if word_key not in targs:
                continue
            
            word = targs[word_key]

            # prefix, suffix just happen to be in n_lexical
            if tname in ['confix', 'con']:
                maximal_suffix = max([int(k) for k in targs if k.isnumeric()], default=0)
                word = reinsert_affix_hyphen(tname, word_key, word, maximal_suffix=maximal_suffix)
            words.append(word)
    
    return langs, words
    
