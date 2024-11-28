import polars as pl
import json
import time

def hydrate_df(df):
    """
    Call json.loads on the columns that are stored as JSON strings
    which are templates, related, and descendants
    """

    # note that Object datatype cannot be written to parquet/arrow
    start = time.time()
    df = df.with_columns([
        pl.col('templates').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('templates_h'),
        pl.col('related').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('related_h'),
        pl.col('descendants').map_elements(lambda x: json.loads(x) if x else [], return_dtype=pl.Object).alias('descendants_h'),
    ])
    end = time.time()

    df = df.drop(['templates', 'related', 'descendants'])

    print(f"Hydrated in {end - start:.2f} seconds")
    return df


def collate_templates(df, desired_templates) -> dict[str, list[dict[str, str]]]:
    """
    collate the templates by their type

    :param df: DataFrame
    :param desired_templates: list of templates to collate
    :return: dictionary of (template name: str) -> list of template arguments
    """
    collated_templates = {x: [] for x in desired_templates}
    for templates in df['templates_h']:
        if not templates:
            continue
        for template in templates:
            if template['name'] in desired_templates:
                collated_templates[template['name']].append(template['args'])
    return collated_templates

