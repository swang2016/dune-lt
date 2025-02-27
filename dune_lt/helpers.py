def validate_query_config(query_config: dict) -> None:

    # check that query is populated
    if not query_config.get("query"):
        raise ValueError(f"'query' param for {query_config.get('name')} is not populated")
    
    # check that if replication key is set, starting_replication_value is also set and vice versa
    if (query_config.get("replication_key") and not query_config.get("starting_replication_value")) or \
       (query_config.get("starting_replication_value") and not query_config.get("replication_key")):
        raise ValueError(f"Both 'replication_key' and 'starting_replication_value' params must be set for {query_config.get('name')}")