import sys
import random
import json
import pandas as pd
import importlib.util
from gensim.models import Word2Vec
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Iterator, List, Dict, Any
import inspect
import numpy as np


class Config:
    """Configuration class that allows dot notation access to config parameters."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize config object from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration parameters
        """
        for key, value in config_dict.items():
            setattr(self, key, value)
    
    def __repr__(self):
        """String representation of config object."""
        attrs = [f"{k}={v}" for k, v in self.__dict__.items()]
        return f"Config({', '.join(attrs)})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config object back to dictionary."""
        return self.__dict__.copy()


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from config.json file.
    
    Args:
        config_path: Path to config.json file. If None, looks in same directory as script.
        
    Returns:
        Dictionary containing configuration parameters
    """
    if config_path is None:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        config_path = script_dir / "config.json"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print(f"Successfully loaded configuration from {config_path}")
        return Config(config)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading config file {config_path}: {e}")
    

def load_schemas_from_index(index_path: str) -> Dict[str, Any]:
    """
    Load schema definitions from the index.py file.
    
    Args:
        index_path: Path to the index.py file
        
    Returns:
        Dictionary containing schema information
    """
    # Convert to absolute path and add parent directory to sys.path
    index_path = Path(index_path).resolve()
    parent_dir = str(index_path.parent)
    
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    try:
        # Import the index module directly
        import schema
        
        # Extract schema instances
        schemas = {
            'product': schema.product_schema,
            'user': schema.user_schema,
            'event': schema.event_schema
        }
        
        print(f"Successfully loaded schemas from {index_path}")
        return schemas
        
    except ImportError as e:
        print(f"Error importing index module: {e}")
        print(f"Make sure {index_path} exists and is valid Python code")
        raise
    except AttributeError as e:
        print(f"Error accessing schema objects: {e}")
        print("Make sure the index file contains: product_schema, user_schema, event_schema")
        raise


def get_schema_field_names(schema) -> Dict[str, str]:
    """
    Extract field names from a schema object.
    
    Args:
        schema: Schema object
        
    Returns:
        Dictionary mapping field types to actual field names
    """
    field_names = {}
    
    # Get all attributes from the schema
    for attr_name in dir(schema):
        if not attr_name.startswith('_'):
            attr_value = getattr(schema, attr_name)
            
            # Check field types based on the schema structure
            if hasattr(attr_value, '__class__'):
                class_name = attr_value.__class__.__name__
                
                if 'IdField' in class_name:
                    field_names['id'] = attr_name
                elif 'CreatedAtField' in class_name:
                    field_names['created_at'] = attr_name
                elif 'SchemaReference' in class_name:
                    # Handle schema references (e.g., product, user)
                    if 'product' in attr_name.lower():
                        field_names['product'] = attr_name
                    elif 'user' in attr_name.lower():
                        field_names['user'] = attr_name
                elif 'String' in class_name and 'event_type' in attr_name:
                    field_names['event_type'] = attr_name
    
    return field_names


def extract_custom_space_from_schema(schema) -> str:
    for attr_name in dir(schema):
        if not attr_name.startswith('_'):
            attr_value = getattr(schema, attr_name)
            if not attr_name.startswith('_'):
                class_name = attr_value.__class__.__name__
                if 'FloatList' in class_name:
                    return attr_name
    print("Make sure customSpace is defined in product schema before training item2vec")
    raise


class DataFrameSentences:
    """
    Iterator that creates sentences from DataFrame data for Word2Vec training.
    """
    
    def __init__(self, events_df: pd.DataFrame, user_col: str, product_col: str, 
                 created_at_col: str, shuffle: bool = False):
        """
        Initialize the sentence iterator.
        
        Args:
            events_df: DataFrame containing events data
            user_col: Column name for user ID
            product_col: Column name for product ID
            created_at_col: Column name for timestamp
            shuffle: Whether to shuffle items within each user's sequence
        """
        self.events_df = events_df
        self.user_col = user_col
        self.product_col = product_col
        self.created_at_col = created_at_col
        self.shuffle = shuffle
        self.len = None
        
        # Preprocess the data
        self._preprocess_data()
    
    def _preprocess_data(self):
        """
        Preprocess the events data to create user sequences.
        """
        # Sort by user and timestamp
        self.events_df = self.events_df.sort_values([self.user_col, self.created_at_col])
        
        # Group by user and create sequences
        self.user_sequences = (
            self.events_df
            .groupby(self.user_col)[self.product_col]
            .apply(lambda x: [str(item) for item in x.tolist()])
            .reset_index()
        )
        
        # Filter out users with only one interaction
        self.user_sequences = self.user_sequences[
            self.user_sequences[self.product_col].apply(len) > 1
        ]
        
        print(f"Created {len(self.user_sequences)} user sequences for training")
    
    def __len__(self):
        """Return the number of sentences (user sequences)."""
        if self.len is not None:
            return self.len
        self.len = len(self.user_sequences)
        return self.len
    
    def __iter__(self):
        """Iterate over user sequences as sentences."""
        for _, row in self.user_sequences.iterrows():
            sequence = row[self.product_col].copy()
            
            if self.shuffle:
                random.shuffle(sequence)
            
            yield sequence
    
    def build_vocab(self, output: str = None) -> Dict[str, int]:
        """
        Build vocabulary from the sequences.
        
        Args:
            output: Optional path to save vocabulary
            
        Returns:
            Dictionary with vocabulary frequencies
        """
        vocab = Counter()
        
        for sequence in self:
            vocab.update(sequence)
        
        vocab_dict = dict(vocab)
        
        if output:
            with open(output, "w") as f:
                json.dump(vocab_dict, f)
        
        return vocab_dict


def load_data(path_str: str, nrows=None) -> pd.DataFrame:
    """
    Load events data from various formats.
    
    Args:
        events_path: Path to events data file
        
    Returns:
        DataFrame containing events data
    """
    path = Path(path_str)
    
    if path.suffix == '.json':
        return pd.read_json(path_str, orient='records', lines=True, nrows=nrows)
    elif path.suffix == '.csv':
        return pd.read_csv(path_str)
    elif path.suffix == '.parquet':
        return pd.read_parquet(path_str, nrows=nrows)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")
    
def get_item_vector(model: Word2Vec, item_id: str, normalize: bool = True) -> List[float]:
    """
    Get normalized vector for an item from the trained Word2Vec model.
    
    Args:
        model: Trained Word2Vec model
        item_id: Item identifier (will be converted to string)
        normalize: Whether to normalize the vector (default: True)
        
    Returns:
        List of floats representing the item vector. Returns zero vector if item not found.
    """
    # Convert item_id to string to match training format
    item_key = str(item_id)
    
    try:
        # Get vector from model
        vector = model.wv[item_key]
        
        # Normalize if requested
        if normalize:
            # Calculate L2 norm
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            # If norm is 0, vector is already all zeros
        
        # Convert to list of floats
        return vector.tolist()
        
    except KeyError:
        # Item not found in vocabulary, return zero vector
        vector_size = model.wv.vector_size
        return [0.0] * vector_size

def main(params):
    """
    Main training function.
    
    Args:
        params: Parsed command line arguments
    """
    # Load schemas from index file
    print("Loading schemas from index file...")
    schemas = load_schemas_from_index(params.index_path)
    
    # Extract field names from schemas
    event_fields = get_schema_field_names(schemas['event'])
    item2vec_product_field = extract_custom_space_from_schema(schemas['product'])
    
    print(f"Event fields: {event_fields}")
    print(f"Item2vec field to be populated in {item2vec_product_field}")
    
    # Load events data
    print("Loading events data...")
    events_df = load_data(params.events_path)
    
    # Map schema field names to actual column names
    user_col = event_fields.get('user', 'user')
    product_col = event_fields.get('product', 'product')
    created_at_col = event_fields.get('created_at', 'created_at')
    
    # If the columns don't exist, try common alternatives
    if user_col not in events_df.columns:
        user_col = 'user_id' if 'user_id' in events_df.columns else 'user'
    if product_col not in events_df.columns:
        product_col = 'product_id' if 'product_id' in events_df.columns else 'product'
    if created_at_col not in events_df.columns:
        created_at_col = 'timestamp' if 'timestamp' in events_df.columns else 'created_at'
    
    print(f"Using columns - User: {user_col}, Product: {product_col}, Timestamp: {created_at_col}")
    
    # Validate columns exist
    required_cols = [user_col, product_col, created_at_col]
    missing_cols = [col for col in required_cols if col not in events_df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in events data: {missing_cols}")
    
    # Create sentence iterator
    print("Creating sentence iterator...")
    train_sentences = DataFrameSentences(
        events_df, user_col, product_col, created_at_col, shuffle=params.shuffle
    )
    
    # Load or create model
    model_path = Path(params.model)
    if model_path.exists():
        print(f"Loading existing model from {params.model}")
        model = Word2Vec.load(params.model)
    else:
        print("Creating new model and building vocabulary...")
        model = Word2Vec(
            epochs=params.epochs, 
            min_count=params.minTF, 
            workers=params.workers, 
            vector_size=params.size, 
            window=params.window
        )
        # Build vocabulary
        vocab_path = Path(params.vocab)
        if vocab_path.exists():
            print(f"Loading vocabulary from {params.vocab}")
            with open(params.vocab, 'r') as f:
                vocab_freq = json.load(f)
        else:
            print("Building vocabulary from data...")
            vocab_freq = train_sentences.build_vocab(output=params.vocab)
        
        model.build_vocab_from_freq(vocab_freq)
        print(f"Vocabulary built with {len(model.wv.index_to_key)} words")
    
    # Train model
    print("Training model...")
    model.train(train_sentences, total_examples=len(train_sentences), epochs=params.epochs)
    
    # Save model
    print(f"Saving model to {params.model}")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(params.model)
    
    print("Training completed successfully!")
    print("Creating vectors for items")
    products_df = load_data(params.products_path)
    products_df[item2vec_product_field] = products_df['id'].apply(lambda x: get_item_vector(model, x, True))
    products_df['has_item2vec_vector'] = products_df[item2vec_product_field].apply(lambda x: 1 if sum(x) != 0 else 0)
    print("Saving data with item2vec")
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "products_df.json"
    products_df.to_json(output_path, orient='records', indent=2)
    print(f"Saved products with item2vec vectors to {output_path}")
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(description='Train Item2Vec model using configuration file')
    
    parser.add_argument('--config', type=str, default=None,
                       help='Path to config.json file (default: config.json in script directory)')
    
    args = parser.parse_args()
    try:
        # Load and validate configuration
        config = load_config(args.config)
        # Run main function with config
        sys.exit(main(config))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)