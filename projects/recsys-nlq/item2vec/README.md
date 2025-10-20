# Item2Vec Implementation for E-commerce Data

## Overview 

Item2Vec is a powerful machine learning model that learns vector representations (embeddings) of items, capturing semantic relationships between them based on user interactions. Inspired by the Word2Vec algorithm, Item2Vec treats user sessions as "sentences" and items as "words." This implementation focuses on e-commerce applications, helping generate meaningful product recommendations based on user behavior patterns.

### Why Item2Vec?
- Captures complex relationships between products based on actual user behavior
- Generates dense vector representations that can be used for similarity searches
- Enables personalized recommendations without requiring explicit product features
- Scales efficiently with large product catalogs

For a detailed technical explanation and industry applications, check out [this article by Grid Dynamics](https://www.griddynamics.com/blog/customer2vec-representation-learning-and-automl-for-customer-analytics-and-personalization).

## Pipeline Architecture

The implementation consists of two main stages:
1. **Data Preprocessing**: Transforms raw e-commerce data into suitable format for training
2. **Item2Vec Training**: Learns product embeddings using modified Word2Vec approach

```
.
├── item2vec/
│   ├── models/               # Trained models and vocabularies
│   └── item2vec.py           # Training implementation
│   └── config.json           # Training config
```

## Getting Started

### Data Preparation

#### Input Data Format
The pipeline expects the events file you will use to ingest historical events and the superlinked schema defenitions.

**Events data** 

The training expects the event data in the schema defined for SL schema.py. The script will read the schema from this file, so you only need to define it once in the SL schema.py.

```
class ProductSchema(sl.Schema):
    id: sl.IdField
    product_image: sl.Blob
    description: sl.String
    topic: sl.StringList
    brand: sl.StringList
    product_type: sl.StringList
    popularity: sl.Float
    item_w2v: sl.FloatList  ### IMPORTANT - ADD THIS IF TRAINING ITEM2VEC
    # hard-filters:
    is_active: sl.Integer
    has_item2vec_vector: sl.Integer ### IMPORTANT - ADD THIS IF TRAINING ITEM2VEC
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

```

IMPORTANT!
1. Running the item2vec process will use the schemas above to infer the relationship between events,users and products.
2. If you are running the item2vec process you HAVE to define superlinked custom space in the name `item_w2v` and integer field `has_item2vec_vector`. As seen above. The training script will add these 2 fields to your products data and output a new file the you can use for dataloading.

## Running the Pipeline

Running the training script is very easy. 

1. **Configure parameters** in `config.json`:
   ```
   {
      "window": 20,
      "size": 100,
      "shuffle": true,
      "workers": 4,
      "minTF": 1,
      "epochs": 2,
      "index_path": "./superlinked_app/index.py",
      "events_path": "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/events.json",
      "products_path": "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/products.json",
      "model": "./item2vec/models/item2vec.model",
      "vocab": "./item2vec/models/vocab.json",
      "events_nrows": 10000,
      "products_nrows": 10000,
      "data_dir": "./data",
      "products_output": "products_df.json"
   }
   ```

3. **Execute the pipeline**:
   ```bash
   python item2vec/item2vec.py
   ```
   if you want to use different location for `config.json` then you can pass it to the script as argument like this:
   ```
   python item2vec/item2vec.py --config YOUR_PATH
   ```

## Configuration Parameters

### Key Parameters Explained

| Parameter | Default | Description | Impact |
|-----------|---------|-------------|---------|
| window | 20 | Context window size | Larger windows capture broader relationships but increase training time |
| size | 100 | Embedding dimension | Higher dimensions capture more nuanced relationships but require more memory |
| minTF | 100 | Minimum item frequency | Higher values reduce noise but might exclude niche products |
| workers | 4 | Training threads | More workers speed up training but increase CPU usage |
| shuffle | true | Randomize item order | Helps prevent position bias in learning |


## Output

The pipeline produces:
1. **Trained Model**: `item2vec/models/w2v.pickle`
2. **Vocabulary Frequency File**: `item2vec/models/vocab.json`
3. **New product data** - The most important output. By default the training will run on every product in your products data and will add 2 columns `item_w2v` that will hold the collaborative vector (and 0 vector if none) and `has_item2vec_vector`, and indicator if the vector is valid (if not means it zeros). You should then upload the data to your bucket or the local path where the superlinked server will load data from.

## Next Steps

After training, this model will be used to genere custom space with SuperLinked, this will allow us:
- Finding similar products based on custom data
- Generating personalized recommendations
- Analyzing product relationships