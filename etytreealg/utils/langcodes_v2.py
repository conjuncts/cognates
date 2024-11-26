# setup
import pandas as pd
df = pd.read_csv('etytreealg/utils/langcodes.csv', delimiter=';')

_langcodes = set(df['code'].values)
def is_langcode(code):
    return code in _langcodes