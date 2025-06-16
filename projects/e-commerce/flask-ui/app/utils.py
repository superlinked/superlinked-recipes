import pandas as pd
from google.cloud import storage
from io import StringIO
import uuid
from flask import session
import requests
from flask import url_for
from urllib.parse import urlparse
import time
import requests
from flask import current_app
from dotenv import main as main_dotenv
import os

def load_products_from_gcs():
    main_dotenv.load_dotenv()
    # products_path = current_app.config['PRODUCTS_GCS_PATH']
    products_path = os.getenv('GCS_PRODUCTS_PATH')
    df = pd.read_csv(products_path, lineterminator='\n')
    return df

def get_random_products(df, n=20):
    """Get n random products from DataFrame"""
    return df.sample(n=min(n, len(df)))

def get_products_by_skus(df, skus):
    """Get products by list of SKUs and keep order"""
    skus = [int(sku) for sku in skus]
    return df[df['sku'].isin(skus)].set_index('sku').loc[skus].reset_index()
    

def get_products_by_category(df, level, category):
    """Get products filtered by category level"""
    return df[df[f'product_category_level_{level}'] == category]

def generate_session_id():
    """Generate unique session ID"""
    return str(uuid.uuid4())

def get_category_hierarchy(df):
    """Get nested category hierarchy"""
    hierarchy = {}
    for level in range(1, 4):
        col = f'product_category_level_{level}'
        if col in df.columns:
            categories = df[col].unique().tolist()
            hierarchy[level] = sorted(categories)
    return hierarchy

def process_image_url(url):
    """Convert HTTP URLs to HTTPS if possible, otherwise proxy through our server"""
    if not url:
        return None
        
    # If it's already HTTPS, return as is
    if url.startswith('https://'):
        return url
        
    # If it's HTTP, try HTTPS version first
    if url.startswith('http://'):
        https_url = 'https://' + url[7:]
        try:
            response = requests.head(https_url, timeout=1)
            if response.status_code == 200:
                return https_url
        except:
            pass
        
        # If HTTPS not available, proxy through our server
        return url_for('main.proxy_image', url=url, _external=True)
        
    return url

def get_nested_category_hierarchy(df):
    """Get nested category hierarchy as a tree structure"""
    hierarchy = {}
    
    # Get unique category combinations
    categories = df[['product_category_level_1', 'product_category_level_2', 'product_category_level_3']].drop_duplicates()
    
    # Build nested dictionary
    for _, row in categories.iterrows():
        level1 = row['product_category_level_1']
        level2 = row['product_category_level_2']
        level3 = row['product_category_level_3']
        
        if level1 not in hierarchy:
            hierarchy[level1] = {}
        
        if level2 not in hierarchy[level1]:
            hierarchy[level1][level2] = []
            
        if level3 and level3 not in hierarchy[level1][level2]:
            hierarchy[level1][level2].append(level3)
    
    return hierarchy

def get_filtered_products(df, level1=None, level2=None, level3=None):
    """Get products filtered by category hierarchy"""
    filtered_df = df.copy()
    
    if level1:
        filtered_df = filtered_df[filtered_df['product_category_level_1'] == level1]
        if level2:
            filtered_df = filtered_df[filtered_df['product_category_level_2'] == level2]
            if level3:
                filtered_df = filtered_df[filtered_df['product_category_level_3'] == level3]
                
    return filtered_df


def fire_event(user_id, sku, event_type):
    """Fire an event to the ingest_event endpoint"""
    event_data = {
        "user": user_id,
        "product": sku,
        "event_type": event_type,
        "created_at": int(time.time())
    }
    
    try:
        base_url = current_app.config['API_BASE_URL']
        response = requests.post(f'{base_url}/api/ingest/event', json=event_data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error firing event: {e}")
        return False

def get_recommendations(endpoint, **params):
    """Generic function to fetch recommendations from various endpoints"""
    try:
        base_url = current_app.config['API_BASE_URL']
        response = requests.get(f'{base_url}/api/search/{endpoint}', params=params)
        response.raise_for_status()
        return [i['id'] for i in response.json()]
    except Exception as e:
        print(f"Error fetching recommendations from {endpoint}: {e}")
        return []