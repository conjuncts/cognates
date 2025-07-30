import polars as pl

# flatten langcodes
from etytreealg.decode.langcodes import EXCEPTIONS, ETYCODES, FAMILIES, LANGCODES

def script3c_flatten_langcodes():
    collector = []
    for codes, dtype in [
        (LANGCODES, 'default'),
        (ETYCODES, 'ety'),
        (FAMILIES, 'family'),
        (EXCEPTIONS, 'exception'),
    ]:
        for k, v in codes.items():
            collector.append((k, v, dtype))
    df = pl.DataFrame(collector, schema=['code', 'name', 'type'], orient='row')
    df.write_parquet('data/step3/langcodes_flat.parquet')
    print("Flattened langcodes and saved to 'data/step3/langcodes_flat.parquet'")
    return df

if __name__ == '__main__':
    script3c_flatten_langcodes()