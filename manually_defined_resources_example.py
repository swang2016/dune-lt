import dlt
import spice

"""
This file shows manuallly defined dlt resources.
The same resources are defined in .dlt/config.toml and
can be dynamically generated via __init__.py
"""

@dlt.resource(
    name="dex_volume",
    primary_key=["project", "_col1"],
    write_disposition="merge"
)
def dex_volume(
        api_key: str = dlt.secrets.value,
    ):
    df = spice.query(
        "https://dune.com/queries/4388",
        api_key=api_key,
        refresh=True,
        cache=False # Spice can cache queries if set to True
    )
    yield df.to_dicts()


@dlt.resource(
    name="dex_volume_incremental",
    primary_key=["project", "date"], # notice we renamed _col1 to date in the forked Dune query
    write_disposition="merge"
)
def dex_volume_incremental(
        api_key: str = dlt.secrets.value,
        cursor=dlt.sources.incremental(cursor_path="date", initial_value="2025-01-01")
    ):
    df = spice.query(
        "https://dune.com/queries/4778954",
        api_key=api_key,
        refresh=True,
        cache=False,
        parameters={"date": cursor.last_value}
    )
    yield df.to_dicts()


@dlt.resource(
    name="y2k_price_data",
    primary_key=["timestamp", "blockchain", "contract_address"],
    write_disposition="merge"
)
def y2k_price_data(
        api_key: str = dlt.secrets.value,
    ):
    df = spice.query(
        4749625,
        api_key=api_key,
        refresh=True,
        cache=False,
        parameters={"symbol": "Y2K"}
    )
    yield df.to_dicts()


@dlt.resource(
    name="custom_sql",
    primary_key="timestamp",
    write_disposition="merge"
)
def custom_sql(
        api_key: str = dlt.secrets.value,
        cursor=dlt.sources.incremental(cursor_path="timestamp", initial_value="2024-11-01")
    ):
    df = spice.query(
        f"""
        SELECT 
            timestamp,
            blockchain,
            contract_address,
            symbol,
            price
        FROM prices.day 
        WHERE symbol = 'BRETT' 
        AND blockchain = 'base'
        AND {cursor.cursor_path} > TIMESTAMP '{cursor.last_value}'
        order by timestamp
        """,
        api_key=api_key,
        refresh=True,
        cache=False,
    )
    yield df.to_dicts()

@dlt.source
def dune_source():
    return [dex_volume, dex_volume_incremental, y2k_price_data, custom_sql]

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="dune_source", destination="duckdb", dataset_name="dune_queries"
    )
    load_info = pipeline.run(dune_source())
    print(load_info)