from superlinked import framework as sl
from superlinked_app.config import settings
from .index import (
    product_schema,
    user_schema,
    topic_space,
    brand_space,
    product_type_space,
    popularity_space,
    price_space,
    item2vec_space,
    image_space,
    product_index,
    description_space,
    brand_text_space
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
            price_space:0
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
            price_space:0
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
            price_space:1
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
            price_space:1
        },
    )
    .find(user_schema)
    .filter(user_schema.user_id == sl.Param("user_id"))
    .select(metadata=[item2vec_space])
)


## NLQ

openai_config = sl.OpenAIClientConfig(
    api_key=settings.open_ai_key.get_secret_value(),
    model=settings.openai_model,
)


popularity_description = (
    "Weight of the popularity - should be a float between 0.0 and 0.2 "
    "Higher value means higher popularity "
    "lower value means lower popularity. "
    "Weight depends on the adjective or noun used to describe the popularity. "
    "For example: "
    "positive weight: 'high popularity', 'popular', 'trendy', 'actual', 'best', 'top-rated'; "
    "negative weight should not be used, ever."
    "0 should be used if no preference for the popularity is found in query explictly"
)

price_space_weight_description = (
    "Weight of the price space that controlls sorting by price. Should be either -0.2, 0 or 0.2"
    "The price weight should always be 0 unless one of the following rules applies on the user query"
    "If variation of the word 'cheap' exists in query -> set price weight to 0.2"
    "If variation of the phrase 'low budget' exists in query -> set price weight to 0.2"
    "If variation of the word 'expensive' exists in query -> set price weight to -0.2"
    "If variation of the word 'luxurious' exists in query -> set price weight to -0.2"
    "Unless one of the above explictly applies set this weight to 0"
)

brand_weight_description = (
    "Brand space weight must be 0.1 if the brand was mentioned in the query, 0 otherwise."
    "Example: 'Black Nike shoe' -> brand weight = 0.1"
    "Example: 'Black trainers' -> brand weight = 0"
    "Example: 'Purple blazer by zimmerman -> brand weight = 0.1"
)

brand_text_description = (
    "Extract the explicit brand name from the user query, do not assume or guess any brand name. if the brand is not mentioned, the value should be empty string. always be on the safeside, extract only brands you know."
    "Example: 'Black Nike shoe' -> Nike"
    "Example: 'Purple blazer by zimmerman -> zimmerman"
    "Example: 'Black trainers' -> ''"
    "Example: 'Purple blazer' -> ''"
    "Example: 'black shoes for men' -> ''"
    "Example: 'Luis vitton leather handbag' -> Luis vitton"
    "Example: 'High heel shoes by ronald donald' -> ronald donald"
)
general_nlq_description = (
    "The natutal query should be extracted from text. The extraction should be the descirption of the product charachersitic only"
)

description_space_weight_description = (
    "This weights must be set to 0.2 if the description space is used, 0 otherwise."
    "Example: 'beige basic cotton shirt' -> 0.2"
    "Example: 'jeans below 100usd' -> 0"
)

query_nli_description_param = sl.Param(
    "description",
    description="Description param shared between image and description spaces. If spotted a spelling mistake - make sure to correct it"
)

query_nli = (
    sl.Query(
        product_index,
        weights={
            topic_space: sl.Param("topic_space_weight", default=0.0),
            brand_space: sl.Param("brand_space_weight", default=0.0),
            product_type_space: sl.Param("product_type_space_weight", default=0.0),
            item2vec_space: sl.Param("item2vec_space_weight", default=0.0),
            #
            image_space: sl.Param("image_space_weight", default=1.0),
            popularity_space: sl.Param(
                "popularity_space_weight",
                description=popularity_description,
                default=0.0,
            ),
            description_space: sl.Param(
                "description_space_weight",
                default=0.1,
                description=description_space_weight_description,
            ),
            brand_text_space: sl.Param(
                "brand_text_space_weight",
                description=brand_weight_description,
                default=0.1,
            ),
            price_space: sl.Param(
                "price_space_weight",
                default=0,
                description=price_space_weight_description
            )
        },
    )
    .find(product_schema)
    .filter(product_schema.is_active > 0)
    .filter(product_schema.price < sl.Param("price_max"))
    .filter(product_schema.price > sl.Param("price_min"))
    .filter(product_schema.category_level_1 == sl.Param(
        'category_level_1',
        description="if category_level_1 can't be infered from query with high confidence, don't use this filter",
        options = ['Women', 'Men', 'Home']
    )
    )
    .similar(
        image_space.description,
        query_nli_description_param,
        weight=sl.Param(
            "description_weight_for_image_space",
            default=1.0,
            description="This weights always must be set to 1.0",
        ),
    )
    .similar(
        description_space,
        query_nli_description_param,
        weight=sl.Param(
            "description_weight_for_description_space",
            default=1.0,
            description="This weights always must be set to 1.0",
        ),
    )
    .similar(
        brand_text_space,
        sl.Param("brand", description=brand_text_description),
        weight=sl.Param(
            "brand_similar_weight",
            default=1.0,
            description="This weights always must be set to 1.0",
        ),
    )
    .with_natural_query(sl.Param("natural_query", description=general_nlq_description), client_config=openai_config)
    .limit(sl.Param("limit", default=100))
)
