# Templates ignored during etymology extraction, i.e., these will not be listed
# in the extracted etymology templates.
import re
from typing import Callable


ignored_etymology_templates: list[str] = [
    "...",
    "IPAchar",
    "ipachar",
    "ISBN",
    "isValidPageName",
    "redlink category",
    "deprecated code",
    "check deprecated lang param usage",
    "para",
    "p",
    "cite",
    "Cite news",
    "Cite newsgroup",
    "cite paper",
    "cite MLLM 1976",
    "cite journal",
    "cite news/documentation",
    "cite paper/documentation",
    "cite video game",
    "cite video game/documentation",
    "cite newsgroup",
    "cite newsgroup/documentation",
    "cite web/documentation",
    "cite news",
    "Cite book",
    "Cite-book",
    "cite book",
    "cite web",
    "cite-usenet",
    "cite-video/documentation",
    "Cite-journal",
    "rfe",
    "catlangname",
    "cln",
    "langname-lite",
    "no deprecated lang param usage",
]
# Regexp for matching ignored etymology template names.  This adds certain
# prefixes to the names listed above.
ignored_etymology_templates_re = re.compile(
    r"^((cite-|R:|RQ:).*|"
    + r"|".join(re.escape(x) for x in ignored_etymology_templates)
    + r")$"
)

wikipedia_templates: set[str] = {
    "wikipedia",
    "slim-wikipedia",
    "w",
    "W",
    "swp",
    "wiki",
    "Wikipedia",
    "wtorw",
}

# Templates that are used to form panels on pages and that
# should be ignored in various positions
PANEL_TEMPLATES: set[str] = {
    "Character info",
    "CJKV",
    "French personal pronouns",
    "French possessive adjectives",
    "French possessive pronouns",
    "Han etym",
    "Japanese demonstratives",
    "Latn-script",
    "LDL",
    "MW1913Abbr",
    "Number-encoding",
    "Nuttall",
    "Spanish possessive adjectives",
    "Spanish possessive pronouns",
    "USRegionDisputed",
    "Webster 1913",
    "ase-rfr",
    "attention",
    "attn",
    "beer",
    "broken ref",
    "ca-compass",
    "character info",
    "character info/var",
    "checksense",
    "compass-fi",
    "copyvio suspected",
    "delete",
    "dial syn",  # Currently ignore these, but could be useful in Chinese/Korean
    "etystub",
    "examples",
    "hu-corr",
    "hu-suff-pron",
    "interwiktionary",
    "ja-kanjitab",
    "ko-hanja-search",
    "look",
    "maintenance box",
    "maintenance line",
    "mediagenic terms",
    "merge",
    "missing template",
    "morse links",
    "move",
    "multiple images",
    "no inline",
    "picdic",
    "picdicimg",
    "picdiclabel",
    "polyominoes",
    "predidential nomics",
    "punctuation",  # This actually gets pre-expanded
    "reconstructed",
    "request box",
    "rf-sound example",
    "rfaccents",
    "rfap",
    "rfaspect",
    "rfc",
    "rfc-auto",
    "rfc-header",
    "rfc-level",
    "rfc-pron-n",
    "rfc-sense",
    "rfclarify",
    "rfd",
    "rfd-redundant",
    "rfd-sense",
    "rfdate",
    "rfdatek",
    "rfdef",
    "rfe",
    "rfe/dowork",
    "rfex",
    "rfexp",
    "rfform",
    "rfgender",
    "rfi",
    "rfinfl",
    "rfm",
    "rfm-sense",
    "rfp",
    "rfp-old",
    "rfquote",
    "rfquote-sense",
    "rfquotek",
    "rfref",
    "rfscript",
    "rft2",
    "rftaxon",
    "rftone",
    "rftranslit",
    "rfv",
    "rfv-etym",
    "rfv-pron",
    "rfv-quote",
    "rfv-sense",
    "selfref",
    "split",
    "stroke order",  # XXX consider capturing this?
    "stub entry",
    "t-needed",
    "tbot entry",
    "tea room",
    "tea room sense",
    # "ttbc", - XXX needed in at least on/Preposition/Translation page
    "unblock",
    "unsupportedpage",
    "video frames",
    "was wotd",
    "wrongtitle",
    "zh-forms",
    "zh-hanzi-box",
}

other_rejects: set[str] = { # I think this is covered by is_panel_template
    "rel-top",
    "rel-bottom"
}

def is_ignored_template(template_name: str) -> bool:
    return template_name in wikipedia_templates or template_name in PANEL_TEMPLATES or template_name in other_rejects or ignored_etymology_templates_re.match(template_name) is not None


class ReducedTemplate:
    def __init__(self, name: str, positional: list[str], keyword: list[str], original_dict: dict=None, original_wikitext: str=None, wikitext_position=None):
        self.name = name
        self.positional = positional
        self.keyword = keyword
        self.original_dict = original_dict
        self.original_wikitext = original_wikitext
        self.wikitext_position = wikitext_position
    
    @staticmethod
    def from_wikitext(template: str) -> 'ReducedTemplate':
        # assert template.startswith('{{') and template.endswith('}}')
        # template = template[2:-2].strip()
        name, *params = template.split('|')
        # remove named parameters, like {{dercat|es|itc-pro|ine-pro|inh=2}}
        positional = []
        keyword = []
        for param in params:
            # remove [[ and ]]
            param = param.replace('[[', '').replace(']]', '')
            if '=' in param:
                keyword.append(param)
            else:
                positional.append(param)
        return ReducedTemplate(name, positional, keyword, original_wikitext=template)
    
    @staticmethod
    def from_dict(template: dict) -> 'ReducedTemplate':
        args = template['args']
        # only obtain the values of the dictionary
        positional = []
        keyword = []
        args = template['args']
        for key, value in args.items():
            if key.isnumeric():
                positional.append(value)
            else:
                keyword.append(key + "=" + value)
        return ReducedTemplate(template['name'], positional, keyword, original_dict=template)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ReducedTemplate):
            return False
        if self.name != value.name:
            return False
        return len(self.positional) == len(value.positional) and len(self.keyword) == len(value.keyword)
    
    def __str__(self) -> str:
        return '{{' + '|'.join([self.name] + self.positional + self.keyword) + '}}'
    
    def __repr__(self) -> str:
        return str(self)
    

def reconstruct_template(wtp_template: dict) -> str:
    # builder = '{{' 
    builder = wtp_template["name"]
    args = wtp_template['args']
    for key, value in args.items():
        # if key is numeric, it is a positional argument
        if key.isnumeric():
            builder += f'|{value}'
        else:
            builder += f'|{key}=' # value may differ
            # {value}'
    
    return builder # + '}}'

# def process_recursive_templates(wikitext) -> list[ReducedTemplate]:
#     textual = []
#     lookback = 0
#     start = 0
#     while True:
#         start = lookback = wikitext.find('{{', lookback)
#         if start == -1: break
#         end = wikitext.find('}}', lookback)
#         while wikitext.count('{{', start+2, end) > 0:
#             # for instance, {{ m {{ foo }}. Then move forward to just match {{foo}}
#             start = wikitext.find('{{', start + 2)
        
#         template = wikitext[start + 2:end]
#         textual.append(ReducedTemplate.from_wikitext(template))
        
#         # excise the processed template from the wikitext to process recursive templates
#         if start == lookback:
#             lookback = end + 2
#         else:
#             wikitext = wikitext[:start] + wikitext[end + 2:]
#     return textual

# def _remove_all_templates(wikitext: str) -> str:
#     # use a stack to remove all templates
#     stack = []
#     i = 0
#     result = ""
#     while i < len(wikitext):
#         if wikitext[i:i+2] == '{{':
#             stack.append(i)
#             i += 2
#         elif wikitext[i:i+2] == '}}' and stack:
#             start = stack.pop()
#             # add text outside of templates to the result
#             if not stack:
#                 result += wikitext[i+2:]
#             i += 2
#         elif not stack:
#             result += wikitext[i]
#             i += 1
#         else:
#             i += 1
#     return result


def _remove_all_templates(wikitext: str) -> str:
    # use a stack to remove all templates
    stack = []
    i = 0
    result_parts = []
    last_i = 0  # keep track of the last index we added to the result
    while i < len(wikitext):
        if wikitext[i:i+2] == '{{':
            # add the text before the template to the result
            if not stack:
                result_parts.append(wikitext[last_i:i])
            stack.append(i)
            i += 2
        elif wikitext[i:i+2] == '}}' and stack:
            stack.pop()
            # if we've exited all templates, remember this index
            if not stack:
                last_i = i + 2
            i += 2
        else:
            i += 1
    # add any remaining text after the last template
    result_parts.append(wikitext[last_i:])
    return ''.join(result_parts)


def process_recursive_templates(wikitext) -> list[ReducedTemplate]:
    textual = []
    stack = []
    i = 0
    while i < len(wikitext):
        if wikitext[i:i+2] == '{{':
            stack.append(i)
            i += 2
        elif wikitext[i:i+2] == '}}' and stack:
            start = stack.pop()
            template = wikitext[start + 2:i]
            template = _remove_all_templates(template)
            reduced = ReducedTemplate.from_wikitext(template)
            reduced.wikitext_position = (start, i+2)
            textual.append(reduced)
            i += 2
        else:
            i += 1
    return textual


def is_subseq(smaller, larger, debugme=False):
    it = iter(larger)
    result = []
    # return all(any(c == ch for c in it) for ch in smaller)
    for ch in smaller:
        for c in it:
            if c == ch:
                if debugme:
                    print(f"Matched {c} with {ch}")
                result.append(c) # build from larger sequence
                # because returning the smaller sequence is simply identity
                break
        else:
            if debugme:
                print(f"Failed to find {ch} in {larger}")
            return None
    return result

def match_templates(wikitext, wtp_templates, debugme=False):    
    reconstructed = [ReducedTemplate.from_dict(template) for template in wtp_templates]
    
    # extract templates from wikitext
    textual = process_recursive_templates(wikitext)
    textual = [x for x in textual if not is_ignored_template(x.name)]

    
    reconstructed_filtered = is_subseq(textual, reconstructed, debugme)
    # assert len(reconstructed_filtered) == len(textual)
    
    if reconstructed_filtered is None:
        print(wikitext)
    
    for text_based, reconstructed in zip(textual, reconstructed_filtered):
        reconstructed.original_wikitext = text_based.original_wikitext
        reconstructed.wikitext_position = text_based.wikitext_position
    
    return reconstructed_filtered

def _pd_obtain_filtered_templates(wikitext, wtp_templates, debugme=False):
    out = match_templates(wikitext, wtp_templates, debugme)
    # return out
    if out is None:
        return None
    return [x.original_dict for x in out]

def insert_expansions(wikitext, templates: list[ReducedTemplate]):
    """
    Insert expanded forms of each template while maintaining the order of the templates
    """
    # sort by the starting position of the template
    # but NOT in place
    templates = templates.copy()
    templates.sort(key=lambda x: x.wikitext_position[0])
    for template in templates[::-1]:
        start, end = template.wikitext_position
        
        full_text = template.original_dict['expansion']
        
        wikitext = wikitext[:start] + full_text + wikitext[start:]
    return wikitext

blacklist_templates = ['glossary', 'root'] # these templates do not need to be expanded


fullnames = {
    "inh": "inherited",
    "der": "derived",
    "bor": "borrowed",
    "cog": "cognate",
    "cal": "calque",
    "affix": "affix",
    "prefix": "prefix",
    "suffix": "suffix",
    'm': 'mention',
}

def insert_expansions_custom(wikitext, templates: list[ReducedTemplate]):
    """
    Custom method of expanding templates.
    """
    # sort by the starting position of the template
    # but NOT in place
    templates = templates.copy()
    templates.sort(key=lambda x: x.wikitext_position[0])
    for template in templates[::-1]:
        start, end = template.wikitext_position
        
        full_text = template.original_dict['expansion']
        
        
        if template.name not in blacklist_templates:
            name = fullnames.get(template.name, template.name)
            
            ttype_text = f" [{name}]"
        else:
            # pass
            ttype_text = ""
        
        wikitext = wikitext[:start] + full_text + ttype_text + wikitext[end:]
        
    return wikitext

def to_textual_unnested(wikitext, templates: list[ReducedTemplate], what_to_do_with_template: Callable[[ReducedTemplate, int], str]):
    """
    Transforms wikitext into textual form. 
    Note: requires that the wikitext is unnested, because otherwise the definition is unclear.
    In the lambda, i starts at 1 (assume that 0 is reserved for the original word)
    """
    # Note: unnested requirement simplifies things a lot, because otherwise
    # From description{{inh desc|en|Latin|fortis|Mentioned word{{m | example}} }}
    # replacing the entire template would destroy inner templates
    
    # Thus we an assume that start1 < end1 < start2 < end2 < ... < startn < endn
    to_expand = templates.copy()
    # assume that they are in sorted order
    l = len(to_expand)
    for i, template in enumerate(to_expand[::-1]):
        start, end = template.wikitext_position
        full_text = what_to_do_with_template(template, l-i)
        wikitext = wikitext[:start] + full_text + wikitext[end:]
    return wikitext
    