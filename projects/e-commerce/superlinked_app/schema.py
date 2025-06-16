from superlinked import framework as sl

class ProductSchema(sl.Schema):
    id: sl.IdField
    product_image: sl.Blob
    description: sl.String
    topic: sl.StringList
    brand: sl.StringList
    product_type: sl.StringList
    popularity: sl.Float
    item_w2v: sl.FloatList
    # hard-filters:
    is_active: sl.Integer
    has_item2vec_vector: sl.Integer
    price: sl.Integer


class UserSchema(sl.Schema):
    user_topic: sl.StringList
    user_brand: sl.StringList
    user_product_type: sl.StringList
    user_item_w2v: sl.FloatList
    user_image: sl.Blob
    user_id: sl.String
    id: sl.IdField


class EventSchema(sl.EventSchema):
    product: sl.SchemaReference[ProductSchema]
    user: sl.SchemaReference[UserSchema]
    event_type: sl.String
    id: sl.IdField
    created_at: sl.CreatedAtField


product_schema = ProductSchema()
user_schema = UserSchema()
event_schema = EventSchema()