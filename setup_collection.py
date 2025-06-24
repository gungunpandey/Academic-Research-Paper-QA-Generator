import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

def setup_qdrant_collection():
    """
    Creates a new collection in Qdrant based on the configuration file.
    """
    # 1. Load configuration and environment variables
    load_dotenv()
    with open('config.json', 'r') as f:
        config = json.load(f)

    QDRANT_URL = os.getenv("QDRANT_URI")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = config.get('collection_name')
    VECTOR_PARAMS = config.get('vector_params')

    if not all([QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, VECTOR_PARAMS]):
        print("Error: Ensure QDRANT_URI, QDRANT_API_KEY, collection_name, and vector_params are set.")
        return

    try:
        # 2. Initialize Qdrant client
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)
        print("Successfully connected to Qdrant.")

        # 3. Create the new collection
        print(f"Attempting to create collection: '{COLLECTION_NAME}'...")
        # Use create_collection which is non-destructive
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(**VECTOR_PARAMS),
        )
        print(f"Successfully created collection '{COLLECTION_NAME}'.")
        print(f"Vector params: size={VECTOR_PARAMS.get('size')}, distance={VECTOR_PARAMS.get('distance')}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("This error can occur if the collection already exists. This is expected and safe.")
        

if __name__ == "__main__":
    setup_qdrant_collection() 