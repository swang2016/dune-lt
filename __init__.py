import dlt
import logging
import spice
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_dune_query_resource(query_config: dict, api_key: str):
    # check that query is populated
    if not query_config.get("query"):
        raise ValueError(f"'query' param for {query_config.get('name')} is not populated")

    # Parse query_params if it exists
    if "query_params" in query_config:
        try:
            query_config["query_params"] = json.loads(query_config["query_params"])
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse query_params JSON for {query_config.get('name')}")
            query_config["query_params"] = {}
    
    @dlt.resource(
        name=query_config.get("name"), # type: ignore
        primary_key=query_config.get("primary_key", None),
        # If primary key is not set, use append disposition
        write_disposition=(
            'append' if not query_config.get("primary_key")
            else query_config.get("write_disposition", "merge")
        ),
    )
    def dune_query(
        api_key: str = api_key,
        cursor=dlt.sources.incremental(
            query_config.get("replication_key"), # type: ignore
            initial_value=query_config.get("starting_replication_value"),
        ) if query_config.get("replication_key") else None,
    ):
        logging.info(f"Extracting data for {query_config.get('name')}")
        if cursor:
            # Incremental loading
            df = spice.query(
                query_config.get("query"), # type: ignore
                api_key=api_key,
                refresh=True,
                parameters=query_config.get("query_params", {}),
                cache=False # TODO: caching is off for now, throws Permission denied (os error 13) sometimes
            )
        else:
            # No incremental loading, just fetch the data
            logging.info(f"No incremental loading config for {query_config.get('name')}, fetching all data.")
            df = spice.query(
                query_config.get("query"), # type: ignore
                api_key=api_key,
                refresh=True,
                parameters=query_config.get("query_params", {}),
                cache=False # TODO: caching is off for now, throws Permission denied (os error 13) sometimes
            )
        logging.info(f"Finished extracting data for {query_config.get('name')}")
        if not query_config.get("primary_key"):
            logging.info(f"No primary key set for {query_config.get('name')}, will use append method to write target table.")
        yield df.to_dicts()

    return dune_query(api_key=api_key)


# Define a source that dynamically creates resources for each query defined in config
@dlt.source
def dune_source(api_key: str = dlt.secrets.value):
    resources = []
    queries = dlt.config.get("dune_queries") # type: ignore
    for query_name, query_config in queries.items():
        query_config["name"] = query_name
        resource = create_dune_query_resource(query_config, api_key)
        resources.append(resource)
    return resources

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="dune_source", destination="duckdb", dataset_name="dune"
    )
    load_info = pipeline.run(dune_source())
    print(load_info)
