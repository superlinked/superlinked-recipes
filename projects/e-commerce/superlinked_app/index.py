import json
import urllib.request
from superlinked import framework as sl
from superlinked_app.config import settings
from superlinked_app.schema import *


def get_categories(path: str) -> dict[str, list[str]]:
    with urllib.request.urlopen(path) as response:
        return json.load(response)

uncategorized_as_category = False

topic_space = sl.CategoricalSimilaritySpace(
    category_input=[user_schema.user_topic, product_schema.topic],
    categories=get_categories(settings.path_topics),
    uncategorized_as_category=uncategorized_as_category,
)

brand_space = sl.CategoricalSimilaritySpace(
    category_input=[user_schema.user_brand, product_schema.brand],
    categories=get_categories(settings.path_brands),
    uncategorized_as_category=uncategorized_as_category,
)

product_type_space = sl.CategoricalSimilaritySpace(
    category_input=[user_schema.user_product_type, product_schema.product_type],
    categories=get_categories(settings.path_product_types),
    uncategorized_as_category=uncategorized_as_category,
)

popularity_space = sl.NumberSpace(
    number=product_schema.popularity, mode=sl.Mode.MAXIMUM, min_value=0, max_value=1
)

item2vec_space = sl.CustomSpace(
    vector=[user_schema.user_item_w2v, product_schema.item_w2v], length=100
)

image_space = sl.ImageSpace(
    image=[
        product_schema.product_image + product_schema.description,
        user_schema.user_image,
    ]
)

event_weights = {
    "product_viewed": 0.5,
    "product_added": 0.7,
    "product_purchased": 1,
    "product_removed": -0.5,
}

product_index = sl.Index(
    spaces=[
        topic_space,
        brand_space,
        product_type_space,
        popularity_space,
        item2vec_space,
        image_space,
    ],
    effects=[
        sl.Effect(
            item2vec_space,
            event_schema.user,
            event_weight * event_schema.product,
            event_schema.event_type == event_type,
        )
        for event_type, event_weight in event_weights.items()
    ]
    + [
        sl.Effect(
            image_space,
            event_schema.user,
            event_weight * event_schema.product,
            event_schema.event_type == event_type,
        )
        for event_type, event_weight in event_weights.items()
    ]
    + [
        sl.Effect(
            topic_space,
            event_schema.user,
            event_weight * event_schema.product,
            event_schema.event_type == event_type,
        )
        for event_type, event_weight in event_weights.items()
    ]
    + [
        sl.Effect(
            brand_space,
            event_schema.user,
            event_weight * event_schema.product,
            event_schema.event_type == event_type,
        )
        for event_type, event_weight in event_weights.items()
    ]
    + [
        sl.Effect(
            product_type_space,
            event_schema.user,
            event_weight * event_schema.product,
            event_schema.event_type == event_type,
        )
        for event_type, event_weight in event_weights.items()
    ],
    fields=[
        product_schema.is_active,
        product_schema.topic,
        product_schema.product_type,
        product_schema.brand,
        product_schema.price,
        product_schema.id,
        product_schema.has_item2vec_vector,
        user_schema.user_id
    ],
    temperature=0.8,
)
