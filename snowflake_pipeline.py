from dune_lt import dune_source # dynamically generates resources based off config.toml
import dlt

if __name__ == "__main__":
    pipeline = dlt.pipeline(
        pipeline_name="dune_source", destination="snowflake", dataset_name="dune_queries"
    )
    load_info = pipeline.run(dune_source())
    print(load_info)