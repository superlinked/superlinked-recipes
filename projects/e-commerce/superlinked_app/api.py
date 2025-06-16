from superlinked.framework.dsl.executor.rest.rest_configuration import RestQuery
from superlinked.framework.dsl.executor.rest.rest_descriptor import RestDescriptor
from superlinked.framework.dsl.executor.rest.rest_executor import RestExecutor
from superlinked.framework.dsl.source.rest_source import RestSource
from superlinked.framework.dsl.registry.superlinked_registry import SuperlinkedRegistry
from superlinked.framework.dsl.source.data_loader_source import (
    DataFormat,
    DataLoaderSource,
    DataLoaderConfig,
)

from superlinked.framework.dsl.storage.redis_vector_database import RedisVectorDatabase
from superlinked.framework.common.parser.dataframe_parser import DataFrameParser

from .index import product_schema, product_index, user_schema, event_schema
from .query import (
    item2item_query,
    user2item_query,
    item_popularity_query,
    topic_popularity_query,
    get_item_custom_space_query,
    get_user_custom_space_query
)
from superlinked_app.config import settings

# parse our data into the schemas - not matching column names can be conformed to schemas using the mapping parameter
product_df_parser = DataFrameParser(schema=product_schema)
user_df_parser = DataFrameParser(schema=user_schema)
event_df_parser = DataFrameParser(schema=event_schema)
# setup our application
source_product: RestSource = RestSource(schema=product_schema, parser=product_df_parser)
source_user: RestSource = RestSource(user_schema)
source_event: RestSource = RestSource(schema=event_schema)

redis_host = settings.redis_vdb_host
redis_port = settings.redis_vdb_port
vector_database = RedisVectorDatabase(host=redis_host, port=redis_port)

## setup the data loader
dl_config = DataLoaderConfig(
    "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/products.json",
    DataFormat.JSON,
    pandas_read_kwargs={
        "lines": True,
        "chunksize": settings.chunk_size,
        "orient": "records"
    },
)
data_loader_source: DataLoaderSource = DataLoaderSource(product_schema, dl_config)
executor = RestExecutor(
    sources=[source_product, source_user, source_event, data_loader_source],
    indices=[product_index],
    queries=[
        RestQuery(RestDescriptor("item2item"), item2item_query),
        RestQuery(RestDescriptor("user2item"), user2item_query),
        RestQuery(RestDescriptor("item_popularity"), item_popularity_query),
        RestQuery(RestDescriptor("topic_popularity"), topic_popularity_query),
        RestQuery(RestDescriptor("product_item2vec"), get_item_custom_space_query),
        RestQuery(RestDescriptor("user_item2vec"), get_user_custom_space_query)
    ],
    vector_database=vector_database,
)

SuperlinkedRegistry.register(executor)
