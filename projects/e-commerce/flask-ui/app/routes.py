from flask import Blueprint, render_template, redirect, url_for, session
from .utils import *

from flask import send_file
import os


from flask import send_file, request, Response
## import jsonify
from flask import jsonify
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from flask import Blueprint, render_template, redirect, url_for, session, make_response
from functools import wraps


main = Blueprint('main', __name__)

def no_cache(view):
    @wraps(view)
    def no_cache_impl(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_impl

@main.route('/')
def index():
    """Landing page with start session button"""
    df = load_products_from_gcs()
    hierarchy = get_nested_category_hierarchy(df)
    return render_template('index.html',
                         hierarchy=hierarchy,
                         current_level1=None,
                         current_level2=None,
                         current_level3=None)

@main.route('/start-session')
def start_session():
    """Initialize session and redirect to home"""
    session['user_id'] = generate_session_id()
    return redirect(url_for('main.home'))

@main.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    
    df = load_products_from_gcs()
    # Get personalized recommendations
    recommended_products = get_recommendations('user_recommendations', 
                                            user_id=session['user_id'], limit=30)
    products = get_products_by_skus(df, recommended_products).to_dict('records')
    
    for product in products:
        if 'product_image' in product:
            product['image'] = process_image_url(product['product_image'])
    
    hierarchy  = get_nested_category_hierarchy(df)
    
    return render_template('home.html', 
                         products=products,
                         hierarchy=hierarchy,
                         current_level1=None,
                         current_level2=None,
                         current_level3=None)


@main.route('/category/<path:category_path>')
def category(category_path):
    """Handle category navigation with nested paths"""
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    
    # Split path into levels
    levels = category_path.split('/')
    level1 = levels[0] if len(levels) > 0 else None
    level2 = levels[1] if len(levels) > 1 else None
    level3 = levels[2] if len(levels) > 2 else None
    
    df = load_products_from_gcs()
    hierarchy = get_nested_category_hierarchy(df)
    products = get_filtered_products(df, level1, level2, level3)
    
    # Process image URLs
    products_list = products.to_dict('records')
    for product in products_list:
        if 'product_image' in product:
            product['product_image'] = process_image_url(product['product_image'])
    
    return render_template('category.html',
                         products=products_list[:500],
                         hierarchy=hierarchy,
                         current_level1=level1,
                         current_level2=level2,
                         current_level3=level3)


@main.route('/product/<sku>')
def product(sku):
    """Product detail page"""
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    
    df = load_products_from_gcs()
    product = df[df['sku'] == int(sku)].iloc[0].to_dict()
    hierarchy = get_nested_category_hierarchy(df)

    # Fire product view event
    fire_event(session['user_id'], sku, 'product_viewed')

    # Get recommendations
    similar_products = get_recommendations('item_similarity', item_id=sku, limit=20)
    complementary_by_users = get_recommendations('item_users_similarity', item_id=sku, limit=20)
    complementary_category = get_recommendations('item_complement_topic', item_id=sku, limit=20)
    popular_for_item = get_recommendations('item_popularity', item_id=sku, limit=20)

    recommendations = {
        'similar': get_products_by_skus(df, similar_products).to_dict('records'),
        'complementary_by_users': get_products_by_skus(df, complementary_by_users).to_dict('records'),
        'complementary_category': get_products_by_skus(df, complementary_category).to_dict('records'),
        'popular_for_item': get_products_by_skus(df, popular_for_item).to_dict('records')
    }

    return render_template('product.html', 
                         product=product,
                         hierarchy=hierarchy,
                         recommendations=recommendations,
                         current_level1=product.get('product_category_level_1'),
                         current_level2=product.get('product_category_level_2'),
                         current_level3=product.get('product_category_level_3'))


@main.route('/add-to-cart/<sku>')
def add_to_cart(sku):
    """Handle add to cart event"""
    if 'user_id' not in session:
        return jsonify({'error': 'No session'}), 401
    
    fire_event(session['user_id'], sku, 'product_added')
    return jsonify({'success': True})


@main.route('/static/images/placeholder.png')
def placeholder_image():
    # Get the directory of the current file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, 'static')
    
    # Create images directory if it doesn't exist
    images_dir = os.path.join(static_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    
    # Path to placeholder image
    placeholder_path = os.path.join(images_dir, 'placeholder.png')
    
    # If placeholder doesn't exist, create a simple one
    if not os.path.exists(placeholder_path):
        img = Image.new('RGB', (200, 200), color='#f0f0f0')
        d = ImageDraw.Draw(img)
        d.text((70, 90), "No Image", fill='#666666')
        img.save(placeholder_path)
    
    return send_file(placeholder_path, mimetype='image/png')



@main.route('/proxy-image')
def proxy_image():
    """Proxy for external HTTP images"""
    url = request.args.get('url')
    if not url:
        return 'No URL provided', 400
        
    try:
        # Fetch the image
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create a response with the image content
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers['Content-Type']
        )
    except Exception as e:
        return str(e), 500

@main.route('/reset-session')
def reset_session():
    """Reset session and return to landing page"""
    session.clear()
    return redirect(url_for('main.index'))


@main.route('/search')
@no_cache
def search():
    if 'user_id' not in session:
        return redirect(url_for('main.index'))
    
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.home'))
    try:
        df = load_products_from_gcs()
        search_similar = get_recommendations('nlq2item', query=query, limit=100)
        products = get_products_by_skus(df, search_similar).to_dict('records')
        
        return render_template('search_results.html',
                             products=products,
                             query=query,
                             hierarchy=get_nested_category_hierarchy(df))
                             
    except Exception as e:
        print(f"Search error: {e}")
        return render_template('search_results.html',
                             products=[],
                             query=query,
                             error="Sorry, there was an error processing your search.")