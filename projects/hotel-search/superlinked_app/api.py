from superlinked import framework as sl

from superlinked_app.index import hotel_schema, index
from superlinked_app.query import query, query_debug
from superlinked_app.config import settings

rest_source_speech = sl.RestSource(hotel_schema)

vector_database = sl.RedisVectorDatabase(
    host=settings.redis_vdb_host, port=settings.redis_vdb_port
)

config = sl.DataLoaderConfig(
    settings.path_dataset,
    sl.DataFormat.JSON,
    pandas_read_kwargs={"lines": True, "chunksize": settings.chunk_size},
)
loader_source_speech = sl.DataLoaderSource(hotel_schema, config)

executor = sl.RestExecutor(
    sources=[
        rest_source_speech,
        loader_source_speech,
    ],
    indices=[index],
    queries=[
        sl.RestQuery(sl.RestDescriptor("hotel"), query),
        sl.RestQuery(sl.RestDescriptor("hotel-debug"), query_debug),
    ],
    vector_database=vector_database,
)

sl.SuperlinkedRegistry.register(executor)
