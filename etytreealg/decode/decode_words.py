import re
import polars as pl

from etytreealg.decode import langcodes as langcodes
from etytreealg.decode.misc_data import _actually_starts_with_asterisk


def _reproduce_transliteration(df):
    # verify that no valid words contain "<t:" or similar
    suspect = df.filter(
        pl.col('word').str.contains('<[a-z]+:'),
    )
    assert suspect.is_empty(), suspect

_macron_remove = {
    u'\u0304': '',
    u'\u0100': 'A',
    u'\u0101': 'a',
    u'\u0102': 'Æ',
    u'\u01e3': 'æ',
    u'\u0112': 'E',
    u'\u0113': 'e',
    u'\u012a': 'I',
    u'\u012b': 'i',
    u'\u014c': 'O',
    u'\u014d': 'o',
    u'\u016a': 'U',
    u'\u016b': 'u',
    u'\u0232': 'Y',
    u'\u0233': 'y',
}

def decode_word(word: str, lang: str = None, langcode: str = None, tkey: str=None, host_template: dict=None) -> str:
    """
    Decodes a word into something which may be found

    tname: template name
    tkey: template key
    Template information is relevant - ie. if the word is a suffix. Then, we can add in the suffix information.
    """

    if lang is None and langcode is None:
        pass # this is difficult

    # handle <t: (transliteration) and similar
    # note that no valid words contain "<t:"
    t_re = r'<[a-z]+:(.*?)>'
    word = re.sub(t_re, '', word)

    # handle reconstruction
    if word.startswith('*'):
        # check if it is a reconstruction
        if langcode is not None:
            lang_req = pl.col('lang_code') == langcode
        elif lang is not None:
            lang_req = pl.col('lang') == lang
        else:
            lang_req = True

        df = _actually_starts_with_asterisk.filter(
            (pl.col('word') == word) &
            lang_req
        )
        if df.shape[0] > 0:
            return word
        
        # it is a reconstruction
        word = word[1:]
    
    if lang is None:
        lang = langcodes.langcode_to_name(langcode)
    if lang and 'Latin' in lang:
        # remove macrons
        for k, v in _macron_remove.items():
            word = word.replace(k, v)
    


    return word
        

if __name__ == "__main__":
    
    templates = {'name': 'suffix', 'args': {'1': 'la', '2': 'Mahomētus<t:Muhammad>', '3': 'ānus'}}

    print(decode_word('Mahomētus<t:Muhammad>', 'Latin'))