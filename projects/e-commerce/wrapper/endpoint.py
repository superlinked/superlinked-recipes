import os
import json
import logging
from threading import Lock
from pathlib import Path
from io import BytesIO
import base64
import uuid
import random
from dotenv import main
from PIL import Image
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from fastapi import FastAPI, HTTPException
import uvicorn
import pandas as pd
import numpy as np
import requests

from kv.redis import RedisKV

# Load environment variables
main.load_dotenv()
__dir__ = Path(__file__).parent.absolute()

# Constants
BASE_SL_URL = f"http://{os.getenv('SUPERLINKED_HOST')}:{os.getenv('SUPERLINKED_PORT')}"
SL_API_MAP = {
    'ingest_event': f"{BASE_SL_URL}/api/v1/ingest/event_schema",
    'ingest_product': f"{BASE_SL_URL}/api/v1/ingest/product_schema",
    'ingest_user': f"{BASE_SL_URL}/api/v1/ingest/user_schema",
    'item2item': f"{BASE_SL_URL}/api/v1/search/item2item",
    'user2item': f"{BASE_SL_URL}/api/v1/search/user2item",
    "product_item2vec": f"{BASE_SL_URL}/api/v1/search/product_item2vec",
    "user_item2vec": f"{BASE_SL_URL}/api/v1/search/user_item2vec",
    'popularity': f"{BASE_SL_URL}/api/v1/search/item_popularity",
    'filtered_popularity': f"{BASE_SL_URL}/api/v1/search/topic_popularity",
    'nlq2item': f"{BASE_SL_URL}/api/v1/search/nlq2item",
    'data_loader_run': f"{BASE_SL_URL}/data-loader/product_schema/run",
}


@dataclass
class AppState:
    """Holds the shared application state."""
    lock: Lock = field(default_factory=Lock, init=False)
    products_df: pd.DataFrame = field(default=None, init=False)
    product_id_to_topic: dict = field(default=None, init=False)
    product_id_to_type: dict = field(default=None, init=False)
    logger: logging.Logger = field(default=None, init=False)
    redis_kv: RedisKV = field(default=None, init=False)
    empty_image: str = field(default=None, init=False)
    query_config: dict = field(default=None, init=False)

    def init(self):
        """Initialize the application state."""
        with self.lock:
            self._setup_logging()
            self._load_redis_kv()
            self._load_data()
            self.empty_image = self._generate_empty_image()
            self.query_config = self._load_query_config()

    def recalc(self):
        """Recalculate application data."""
        with self.lock:
            self._load_data()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()

    def _load_redis_kv(self):
        redis_credentials = {'host': os.getenv('REDIS_HOST'), 'port': os.getenv('REDIS_PORT')}
        self.redis_kv = RedisKV(credentials=redis_credentials)

    def _load_data(self):
        products_df = pd.read_json(os.getenv('PRODUCT_DATASET_PATH'), lines=True)
        self.products_df = products_df
        self.product_id_to_topic = products_df.set_index("id")["topic"].to_dict()
        self.product_id_to_type = products_df.set_index("id")["product_type"].to_dict()

    def _generate_empty_image(self):
        empty_image = Image.new('RGB', (255, 255))
        buffered = BytesIO()
        empty_image.save(buffered, format="JPEG")
        return "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/images/blank_image.jpg" ## TODO handle this
        ## return PIL empty image not base64
        # return empty_image


    def _load_query_config(self):
        config_path = __dir__ / "config" / "query_config.json"
        with open(config_path, 'r') as config_file:
            return json.load(config_file)


@asynccontextmanager
async def startup_event(app: FastAPI):
    """Handles app startup."""
    global app_state
    try:
        app_state = AppState()
        app_state.init()
        yield
    except Exception as e:
        app_state.logger.error(f"Error during startup: {e}")


def call_sl_url(path_name, data=None):
    """Makes an HTTP POST request to an SL API endpoint."""
    url = SL_API_MAP.get(path_name)
    if not url:
        raise ValueError(f"Invalid path name: {path_name}")
    
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, json=data or {})
        response.raise_for_status()
        
        # Check if response has content
        if not response.text.strip():
            app_state.logger.info(f"Empty response from {path_name} - code {response.status_code}")
            return response.status_code, {}
        
        # Try to parse as JSON
        try:
            return response.status_code, response.json()
        except json.JSONDecodeError as json_error:
            app_state.logger.error(f"JSON decode error for {path_name}: {json_error}")
            app_state.logger.error(f"Response content: {response.text[:200]}...")  # Log first 200 chars
            return response.status_code, {"error": "Invalid JSON response", "raw_response": response.text}
            
    except requests.exceptions.RequestException as req_error:
        app_state.logger.error(f"Request error for {path_name}: {req_error}")
        return 500, {"error": str(req_error)}
        
    except Exception as e:
        app_state.logger.error(f"Unexpected error in SL call for {path_name}: {e}")
        return 500, {"error": str(e)}


def get_user_dummy_vector(user_id):
    """Creates a dummy user vector."""
    return {
        "id": user_id,
        "user_id": user_id,
        "user_topic": "",
        "user_brand": "",
        "user_product_type": "",
        "user_item_w2v": [0.0] * 100,
        "user_image": app_state.empty_image
    }

def get_collaborative_vector(sl_results):
    normalize = lambda x: x / np.linalg.norm(x) if np.linalg.norm(x) > 0 else x
    return normalize(np.mean([i['metadata']['vector_parts'][0] for i in sl_results['entries']], axis=0)).tolist()

def get_item2vec(item_id, entity_type='item'):
    if entity_type == 'item':
        _, data = call_sl_url("product_item2vec", {"product_id": item_id})
    else:
        _, data = call_sl_url("user_item2vec", {"user_id": item_id})
    item2vec_vector = data['entries'][0]['metadata']['vector_parts'][0]
    return item2vec_vector

def check_user_exist(id):
    _, data = call_sl_url("user_item2vec", {"user_id": id})
    return len(data['entries']) > 0

def populate_collobarative_by_neighbors(_id, _type, limit=10):
    param = 'cb_neighbors_user' if _type == 'user' else 'cb_neighbors_item'
    data = app_state.query_config.get(param)['params']
    data['limit'] = limit
    if _type == 'user':
        data['user_id'] = str(_id)
    else:
        data['product_id'] = str(_id)
    if _type == 'user':
        _, results = call_sl_url("user2item", data=data)
    else:
        _, results = call_sl_url("item2item", data=data)
    return get_collaborative_vector(results)

def clean_metadata_from_results(results):
    cleaned = []
    for item in results:
        cleaned_item = item.copy()
        if 'metadata' in cleaned_item and 'vector_parts' in cleaned_item['metadata']:
            cleaned_item['metadata'] = {k: v for k, v in cleaned_item['metadata'].items() if k != 'vector_parts'}
        cleaned.append(cleaned_item)
    return cleaned

def get_popularity(topic=None, product_type=None, user_id=None, limit=10):
    """Returns popular item recommendations."""
    limit = int(limit)
    if user_id:
        user_topics = app_state.redis_kv.get_user_topics(user_id, top=3)
        if user_topics:
            recs = []
            for topic in user_topics:
                _, results = call_sl_url("filtered_popularity", data={"query_topic": topic, "query_product_type": "", "limit": 100})
                results_list = results['entries']
                random.shuffle(results_list)
                recs.append(results_list[:limit])
            ## shuffle the results randomly and return the top limit
            return [item for sublist in zip(*recs) for item in sublist][:limit]
    if topic:
        _, results = call_sl_url("filtered_popularity", data={"query_topic": topic, "query_product_type": product_type or "", "limit": 100})
    else:
        _, results = call_sl_url("popularity", data={"limit": max(limit ,100)})
    results_list = results['entries']
    ##shuffle the results randomly and return the top limit
    random.shuffle(results_list)
    return results_list[:limit]

# FastAPI App
app = FastAPI(lifespan=startup_event)

@app.post("/api/ingest/event")
async def ingest_event(event: dict):
    try:
        app_state.logger.info(f"Event ingestion: {event}")
        if 'id' not in event:
            event['id'] = str(uuid.uuid4().hex)
        user_id = event['user']
        product_id = event['product']
        topic = app_state.product_id_to_topic.get(int(product_id))
        
        if topic is None:
            return {"status": "failed", "err": f"Missing data for product {product_id}"}
        
        user_topic_id = f"{user_id}_{topic}"
        if not check_user_exist(user_topic_id):
            app_state.logger.info(f"No existing vectors for user {user_topic_id} - creating dummy user..")
            user_dummy_data = get_user_dummy_vector(user_topic_id)
            app_state.logger.info(f"User ingestion: {user_dummy_data}")
            user_ingest_code, _ = call_sl_url("ingest_user", user_dummy_data)
            if 200 <= user_ingest_code < 300:
                event["user"] = user_topic_id
                event_ingest_code, _ = call_sl_url("ingest_event", event)
                
                if 200 <= event_ingest_code < 300:
                    app_state.redis_kv.set_user_event_topic(user_id, topic ,event['created_at'])
                    return {"status": "success", "err": ""}
        else:
            event["user"] = user_topic_id
            event_ingest_code, _ = call_sl_url("ingest_event", event)
            if 200 <= event_ingest_code < 300:
                app_state.redis_kv.set_user_event_topic(user_id, topic ,event['created_at'])
                return {"status": "success", "err": ""}
    
    except Exception as e:
        app_state.logger.error(f"Event ingestion failed g: {e}")
        return {"status": "failed", "err": str(e)}

    
@app.post("/api/ingest/product")
async def ingest_product(product_data):
    """Handles product ingestion."""
    await call_sl_url('ingest_product', data=product_data)
    app_state.recalc()


@app.post("/api/ingest/data_load")
async def load_data_from_source():
    """Handles event ingestion."""
    call_sl_url('data_loader_run')
    app_state.recalc()


@app.get("/api/search/user_recommendations")
async def get_user_recommendations(user_id, limit=10):

    """Returns user recommendations."""
    try:
        user_topics = app_state.redis_kv.get_user_topics(user_id, top=3)
        if not user_topics:
            raise Exception("User vectors doesn't exists")
        user_topic_ids = [f"{user_id}_{topic}" for topic in user_topics]
        query_data = app_state.query_config.get('user')['params']
        query_data['limit'] = int(limit)
        recs = []
        for uid in user_topic_ids:
            product_item2vec = get_item2vec(uid, 'user')
            if sum(product_item2vec) == 0:
                collobarative_vector = populate_collobarative_by_neighbors(uid, 'user', 5)
            else:
                collobarative_vector = product_item2vec
            uid_data = query_data
            uid_data['user_id'] = uid
            uid_data['collaborative_vector'] = collobarative_vector
            _, results = call_sl_url("user2item", data=uid_data)
            recs.append(results['entries'])
        results = [item for sublist in zip(*recs) for item in sublist][:int(limit)]
        return clean_metadata_from_results(results)
    except Exception as e:
        app_state.logger.error(f"Error getting user recommendations: {e}, fallback to popularity")
        results = get_popularity(user_id=user_id, limit=limit)
        return clean_metadata_from_results(results)


@app.get("/api/search/item_similarity")
async def get_item_similarity(item_id, limit=10):
    """Returns similar item recommendations."""
    logger = app_state.logger
    item_topic = app_state.product_id_to_topic.get(int(item_id))
    item_type = app_state.product_id_to_type.get(int(item_id))
    query_data = app_state.query_config.get('item_similarity')['params']
    query_data['limit'] = int(limit)
    query_data['product_id'] = str(item_id)
    try:
        product_item2vec = get_item2vec(item_id)
        if sum(product_item2vec) == 0:
            collobarative_vector = populate_collobarative_by_neighbors(item_id, 'item', 5)
        else:
            collobarative_vector = product_item2vec
        query_data['collaborative_vector'] = collobarative_vector
        _, results = call_sl_url("item2item", data = query_data)
        return clean_metadata_from_results(results['entries'])
    except Exception as e:
        app_state.logger.error(f"Error getting item similarity: {e}, fallback to popularity")
        results = get_popularity(topic=item_topic, product_type=item_type, limit=limit)
        return clean_metadata_from_results(results)


@app.get("/api/search/item_users_similarity")
async def get_item_similarity(item_id, limit=10):
    """Returns similar item recommendations."""
    logger = app_state.logger
    item_topic = app_state.product_id_to_topic.get(int(item_id))
    item_type = app_state.product_id_to_type.get(int(item_id))
    query_data = app_state.query_config.get('item_users_similarity')['params']
    query_data['limit'] = int(limit)
    query_data['product_id'] = str(item_id)
    try:
        product_item2vec = get_item2vec(item_id)
        if sum(product_item2vec) == 0:
            collobarative_vector = populate_collobarative_by_neighbors(item_id, 'item', 5)
        else:
            collobarative_vector = product_item2vec
        query_data['collaborative_vector'] = collobarative_vector
        _, results = call_sl_url("item2item", data = query_data)
        return clean_metadata_from_results(results['entries'])
    except Exception as e:
        app_state.logger.error(f"Error getting item similarity: {e}, fallback to popularity")
        results =  get_popularity(topic=item_topic, product_type=item_type, limit=limit)
        return clean_metadata_from_results(results)


@app.get("/api/search/item_complement_type")
async def get_item_type_complementary(item_id, limit=10):
    """Returns complementary type item recommendations."""
    logger = app_state.logger
    item_topic = app_state.product_id_to_topic.get(int(item_id))
    item_type = app_state.product_id_to_type.get(int(item_id))
    query_data = app_state.query_config.get('item_complementary_type')['params']
    query_data['limit'] = int(limit)
    query_data['product_id'] = str(item_id)
    try:
        product_item2vec = get_item2vec(item_id)
        if sum(product_item2vec) == 0:
            collobarative_vector = populate_collobarative_by_neighbors(item_id, 'item', 5)
        else:
            collobarative_vector = product_item2vec
        query_data['collaborative_vector'] = collobarative_vector
        _, results = call_sl_url("item2item", data = query_data)
        return clean_metadata_from_results(results['entries'])
    except Exception as e:
        app_state.logger.error(f"Error getting item type complementary - {e}, fallback to popularity")
        results = get_popularity(topic=item_topic, product_type=item_type, limit=limit)
        return clean_metadata_from_results(results)


@app.get("/api/search/item_complement_topic")
async def get_item_type_complementary(item_id, limit=10):
    """Returns complementary topic item recommendations."""
    logger = app_state.logger
    item_topic = app_state.product_id_to_topic.get(int(item_id))
    item_type = app_state.product_id_to_type.get(int(item_id))
    query_data = app_state.query_config.get('item_complementary_topic')['params']
    query_data['limit'] = int(limit)
    query_data['product_id'] = str(item_id)
    try:
        product_item2vec = get_item2vec(item_id)
        if sum(product_item2vec) == 0:
            collobarative_vector = populate_collobarative_by_neighbors(item_id, 'item', 5)
        else:
            collobarative_vector = product_item2vec
        query_data['collaborative_vector'] = collobarative_vector
        _, results = call_sl_url("item2item", data = query_data)
        return clean_metadata_from_results(results['entries'])
    except Exception as e:
        app_state.logger.error(f"Error getting item topic complementary - {e}, fallback to popularity")
        results =  get_popularity(topic=item_topic, product_type=item_type, limit=limit)
        return clean_metadata_from_results(results)

@app.get("/api/search/nlq2item")
async def get_item_by_nli(query, limit=10):
    """Returns item recommendations based on natural language query."""
    query_data = {}
    query_data['natural_query'] = query
    query_data['limit'] = int(limit)
    try:
        _, results = call_sl_url("nlq2item", data=query_data)
        return clean_metadata_from_results(results['entries'])
    except Exception as e:
        app_state.logger.error(f"Error getting item by NLI: {e}")
        results = get_popularity(limit=limit)
        return clean_metadata_from_results(results)

@app.get("/api/search/item_popularity")
async def get_item_popularity(item_id, limit=10):
    """Returns popular item recommendations."""
    item_topic = app_state.product_id_to_topic.get(int(item_id))
    item_type = app_state.product_id_to_type.get(int(item_id))
    results =  get_popularity(topic=item_topic, product_type=item_type, limit=limit)
    return clean_metadata_from_results(results)

@app.get("/api/get_user_topics")
async def get_user_topics(user_id):
    return app_state.redis_kv.get_user_topics(user_id, top=0)


if __name__ == "__main__":
    uvicorn.run("__main__:app", host="127.0.0.1", port=8000)
