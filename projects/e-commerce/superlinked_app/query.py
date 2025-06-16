from superlinked import framework as sl
from superlinked_app.config import settings
from .index import (
    product_schema,
    user_schema,
    topic_space,
    brand_space,
    product_type_space,
    popularity_space,
    item2vec_space,
    image_space,
    product_index,
)


item2item_query = (
    sl.Query(
        product_index,
        weights={
            topic_space: sl.Param("topic_weight"),
            brand_space: sl.Param("brand_weight"),
            product_type_space: sl.Param("product_type_weight"),
            popularity_space: sl.Param("popularity_weight"),
            item2vec_space: sl.Param("item2vec_weight"),
            image_space: sl.Param("image_weight"),
        },
    )
    .find(product_schema)
    .with_vector(product_schema, sl.Param("product_id"))
    .similar(item2vec_space, sl.Param("collaborative_vector"))
    .filter(product_schema.is_active >= sl.Param("is_active", default=1))
    .filter(product_schema.has_item2vec_vector == sl.Param("has_item2vec_vector"))
    .select(metadata=[item2vec_space])
    .limit(sl.Param("limit", default=100))
)

item_popularity_query = (
    sl.Query(
        product_index,
        weights={popularity_space: 1},
    )
    .find(product_schema)
    .filter(product_schema.is_active > 0)
    .select_all()
    .limit(sl.Param("limit"))
)

topic_popularity_query = (
    sl.Query(
        product_index,
        weights={popularity_space: 1, topic_space: 1, product_type_space: 1},
    )
    .find(product_schema)
    .similar(topic_space, sl.Param("query_topic"))
    .similar(product_type_space, sl.Param("query_product_type"))
    .filter(product_schema.is_active > 0)
    .select(metadata=[item2vec_space])
    .limit(sl.Param("limit", default=100))
)


user2item_query = (
    sl.Query(
        product_index,
        weights={
            topic_space: sl.Param("topic_weight"),
            brand_space: sl.Param("brand_weight"),
            product_type_space: sl.Param("product_type_weight"),
            item2vec_space: sl.Param("item2vec_weight"),
            image_space: sl.Param("image_weight"),
            popularity_space: 0,
        },
    )
    .find(product_schema)
    .with_vector(user_schema, sl.Param("user_id"))
    .similar(item2vec_space, sl.Param("collaborative_vector"))
    .filter(product_schema.is_active >= sl.Param("is_active", default=1))
    .filter(product_schema.has_item2vec_vector == sl.Param("has_item2vec_vector"))
    .select(metadata=[item2vec_space])
    .limit(sl.Param("limit", default=100))
)


get_item_custom_space_query = (
    sl.Query(
        product_index,
        weights={
            topic_space: 1,
            brand_space: 1,
            product_type_space: 1,
            item2vec_space: 1,
            image_space: 1,
            popularity_space: 1,
        },
    )
    .find(product_schema)
    .filter(product_schema.id == sl.Param("product_id"))
    .select(metadata=[item2vec_space])
)

get_user_custom_space_query = (
    sl.Query(
        product_index,
        weights={
            topic_space: 1,
            brand_space: 1,
            product_type_space: 1,
            item2vec_space: 1,
            image_space: 1,
            popularity_space: 1,
        },
    )
    .find(user_schema)
    .filter(user_schema.user_id == sl.Param("user_id"))
    .select(metadata=[item2vec_space])
)