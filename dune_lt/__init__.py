import dlt
import logging
import spice
from spice._extract import _is_sql
import json

from dune_lt.helpers import validate_query_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_dune_query_resource(query_config: dict, api_key: str) -> dlt.resource:

    # validate query config
    validate_query_config(query_config)
    
    @dlt.resource(
        name=query_config.get("name"), # type: ignore
        primary_key=query_config.get("primary_key", None),
        write_disposition=(
            'append' if not query_config.get("primary_key") # If primary key is not set, use append disposition
            else query_config.get("write_disposition", "merge")
        ),
    )
    def dune_query(
        api_key: str = api_key,
        cursor=dlt.sources.incremental(
            cursor_path=query_config.get("replication_key"), 
            initial_value=query_config.get("starting_replication_value")
            ) if query_config.get("replication_key") else None,
    ):
        logging.info(f"Extracting data for {query_config.get('name')}")

        # parse query params
        params = query_config.get("query_params", "{}")
        params = json.loads(params)

        # Get the base query
        query = query_config.get("query")

        # incremental loading
        if cursor:
            logging.info(f"Incrementally loading data for {query_config.get('name')}")
            if _is_sql(query_config.get("query")):
                # detected that query is a SQL query, replace the replication key and cursor with the actual values
                query = query.replace("{replication_key}", query_config.get("replication_key"))
                query = query.replace("{cursor_value}", cursor.last_value)
            else:
                # detected that query is a url or query id, pass in the replication key and cursor as params
                params[query_config.get("replication_key")] = cursor.last_value
            df = spice.query(
                query,
                api_key=api_key,
                refresh=True,
                parameters=params,
                cache=False # TODO: caching is off for now, throws Permission denied (os error 13) sometimes
            )
        # No incremental loading, just fetch the data
        else:
            logging.info(f"No incremental loading config for {query_config.get('name')}, fetching all data.")
            df = spice.query(
                query,
                api_key=api_key,
                refresh=True,
                parameters=params,
                cache=False # TODO: caching is off for now, throws Permission denied (os error 13) sometimes
            )
        logging.info(f"Finished extracting data for {query_config.get('name')}")
        if not query_config.get("primary_key"):
            logging.info(f"No primary key set for {query_config.get('name')}, will use append method to write target table.")
        yield df.to_dicts()

    return dune_query(api_key=api_key)


# Define a source that dynamically creates resources for each query defined in config
@dlt.source
def dune_source(api_key: str = dlt.secrets.value) -> list[dlt.resource]:
    resources = []
    queries = dlt.config.get("dune_queries") # type: ignore
    for query_name, query_config in queries.items():
        query_config["name"] = query_name
        resource = create_dune_query_resource(query_config, api_key)
        resources.append(resource)
    return resources
