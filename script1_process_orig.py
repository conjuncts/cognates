"""
From the MEDIAWIKI dump, extract the unexpanded wikitexts.

"""


import xml.etree.ElementTree as ET
import pandas as pd
def extract_word_info(xml_file):
    context = iter(ET.iterparse(xml_file, events=('start', 'end')))
    _, root = next(context)  # Get the root element

    # ns = '{http://www.mediawiki.org/xml/export-0.10/}'
    ns = {'mw': 'http://www.mediawiki.org/xml/export-0.10/'}  # Define the namespace
    mw = '{' + ns['mw'] + '}'
    # print("here")
    for event, elem in context:
        # print(elem.tag, elem.text[:100] if elem.text else None, elem.attrib)
        if event == 'end' and elem.tag == f'{mw}page':
            title = elem.find(f'mw:title', namespaces=ns)
            title = title.text if title is not None else None
            text = elem.find(f'.//mw:text', namespaces=ns)
            text = text.text if text is not None else None

            language = None
            # etymology_section = None
            etymology_number = None
            etymology_text = []
            in_etymology = False
            
            if text:
                lines = text.split('\n')
                
                for line in lines:
                    # count number of "=" that start the line
                    # if 2, then it's a language section
                    indent_level = len(line) - len(line.lstrip('='))
                    
                    if in_etymology and indent_level > 0: # 1 <= indent_level <= 3:
                        if etymology_text:
                            yield title, language, etymology_number, ' '.join(etymology_text)
                        in_etymology = False
                        etymology_text = []
                    
                    if indent_level == 2:  # Capture the language section
                        language = line.strip('= ').strip()
                    elif line.startswith('===Etymology'):
                        # etymology_section = line
                        _num = len('===Etymology')
                        etymology_number = line[_num:].strip('= ').strip()
                        etymology_text = []  # Reset etymology_text for the next etymology section
                        in_etymology = True
                    elif in_etymology and indent_level == 0:  # Capture all lines that are not section headers
                        etymology_text.append(line.strip())
                if in_etymology and etymology_text:  # Yield the last etymology section
                    yield title, language, etymology_number, ' '.join(etymology_text)
                in_etymology = False
                etymology_text = []

            root.clear()  # Free up memory

if __name__ == '__main__':
    xml_file = 'data/raw/enwiktionary-20240501-pages-articles.xml'
    # xml_file = 'enwiktionary-20240501-pages-articles.xml'
    data = []
    for word, language, etymology_number, etymology_text in extract_word_info(xml_file):
        # only extract if it has > 1 template in the etymology section
        num_templates = etymology_text.count('{{')
        if num_templates < 2:
            continue
        data.append((word, language, etymology_number, etymology_text))
        if len(data) % 10000 == 0:
            # save to file
            df = pd.DataFrame(data, columns=["word", "lang", "etymology_number", "etymology_text"])
            df.to_csv('data/step1/wikitexts.csv', mode='a', header=False, index=False)
            data = []
            del df
    # save the remaining data
    with open('data/step1/wikitexts.csv', 'a', encoding='utf-8') as f:
        df = pd.DataFrame(data, columns=["word", "lang", "etymology_number", "etymology_text"])
        df.to_csv(f, mode='a', header=False, index=False)