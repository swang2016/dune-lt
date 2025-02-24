# dune-lt

A dlt source that uses [DLT (Data Load Tool)](https://dlthub.com/docs/intro) to extract data from [Dune Analytics](https://dune.com/) queries and load into your destination of [choice](https://dlthub.com/docs/dlt-ecosystem/destinations/). In the examples shown in this repo, we use DuckDB and Snowflake as the destination. Jump to the [Example Usage: DuckDB](#example-usage-duckdb) and [Example Usage: Snowflake](#example-usage-snowflake) sections to see how to use the source.

This source allows you to:

- Configure multiple Dune queries in a single config file (`.dlt/config.toml`)
- dlt resources are created automatically based on the queries defined in the config file
- Accepts Dune query IDs, query URLs, or SQL as input for the queries
- Accepts query parameters if the Dune query is [parameterized](https://docs.dune.com/web-app/query-editor/parameters)
- Extract data incrementally using replication keys

The heavy lifting is done by `dlt` and [`spice`](https://github.com/paradigmxyz/spice), a Python package released by the Paradigm team to interact with the Dune REST API. I merely wrapped it in a `dlt` source, so all credit goes to the `dlt` and `spice` teams!

## Installation

### Using Poetry (recommended)

1. Clone this repository:
```bash
git clone https://github.com/swang2016/dune-lt.git
cd dune-lt
```

2. Install Poetry if you haven't already:
[Poetry Installation Guide](https://python-poetry.org/docs/#installation)

3. Install dependencies using Poetry:
```bash
poetry install
```

4. Activate the Poetry shell:
```bash
poetry shell
```

## Configuration

The tool uses a TOML configuration file (`.dlt/config.toml`) to define your Dune queries (see dtl docs on [configurations](https://dlthub.com/docs/general-usage/credentials/)). Each query is configured under the `dune_queries` section. Here's an example configuration:

```toml
[dune_queries.dex_volume] # loads data from the Dune query with the ID 4388 into a table called "dex_volume"
query = "https://dune.com/queries/4388"
primary_key = ["project", "_col1"]
replication_key = "_col1"
write_disposition = "merge"

[dune_queries.custom_sql] # loads data from a custom SQL query into a table called "custom_sql"
query = """
SELECT 
    timestamp,
    blockchain,
    contract_address,
    symbol,
    price
FROM prices.day 
WHERE symbol = 'BRETT' 
AND blockchain = 'base'
"""
primary_key = "timestamp"
replication_key = "timestamp"
write_disposition = "merge"
```

### Configuration Options

- `query`: Either a Dune query URL, query ID, or custom SQL query
- `primary_key`: Column(s) that uniquely identify each row (optional)
- `replication_key`: Column used for incremental loading (optional)
- `write_disposition`: Either "merge", "replace", or "append" (forces "append" if no primary key)
- `query_params`: JSON string of parameters for parameterized queries (optional)

### Example with query parameters
Some Dune queries are parameterized ([example](https://dune.com/queries/4749625)), meaning they accept one or more parameters. You can pass these parameters to the query by setting the `query_params` option.

```toml
[dune_queries.y2k_price_data]
query = 4749625 # https://dune.com/queries/4749625
query_params = '{"symbol": "Y2K"}'
```

## Example Usage: DuckDB

1. Set your Dune API as a secret in DLT:
 * In the `.dlt/` directory, create a file called `secrets.toml`
 * Add the following to the file:
```toml
[dune_source]
api_key = "your-dune-api-key"
```

2. Run the pipeline:
```bash
python duckdb_pipeline.py
```

This will:
1. Read the Dune queries defined in your config file
2. Extract data from Dune Analytics via Dune's REST API
3. Load the data into a DuckDB database named `dune_source.duckdb`

### Examining the Data in DuckDB

You can examine the extracted data using the provided Jupyter notebook `examine_tables.ipynb`. The notebook shows how to:

1. Connect to the DuckDB database
2. Query the extracted tables
3. View the data as pandas DataFrames

Example tables created by the default configuration:
- `dex_volume`: DEX trading volume data
- `y2k_price_data`: Price data for Y2K token with primary key
- `y2k_price_data_no_pk`: Same data but in append-only mode
- `custom_sql`: Custom defined SQL query results

dlt also supports a built-in streamlit app for exploring the data in the DuckDB database. To run the app, run the following command:

```bash
dlt pipeline dune_source show
```

## Example Usage: Snowflake

1. Set your Dune API as a secret in DLT:
 * In the `.dlt/` directory, create a file called `secrets.toml`
 * Add the following to the file:
```toml
[dune_source]
api_key = "your-dune-api-key"
```
2. Set your Snowflake credentials as a secret in DLT:
 * In the `.dlt/` directory, create a file called `secrets.toml`
 * Add the following to the file:
```toml
[destination.snowflake.credentials]
database = "<your-database>"
password = "<your-password>"
username = "<your-username>"
host = "<your-host>"
warehouse = "<your-warehouse>"
role = "<your-role>"
```
3. Run the pipeline:
```bash
python snowflake_pipeline.py
```
Same as the DuckDB example, this will load the Dune queries specificed in the `config.toml` file into Snowflake.

## Important Notes

- Make sure to close any duckdb database connections before running the pipeline again
- For queries without a primary key, data will be appended rather than merged
- Incremental loading is supported when a replication key is specified 
- `spice` supports cached queries but I've turned those off for now. Getting `Permission denied (os error 13)` error on one of my machines. If you want to turn caching on you can do so in the `__init__.py` file.