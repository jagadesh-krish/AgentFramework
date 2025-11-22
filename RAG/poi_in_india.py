import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json

client = chromadb.HttpClient(
    host=os.environ.get("CHROMA_DB_HOST", "localhost"),
    port=os.environ.get("CHROMA_DB_PORT", 8000)
)


# Create / get a collection for places
collection = client.get_or_create_collection("poi_india")

# Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Query function: search places by description/query
def query_places(query_text, top_k=5):
    query_embedding = model.encode([query_text]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)
    return results["metadatas"][0]


if __name__ == "__main__":
    # Used to ingest places data into Chroma
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Define the path for the india.json file
    DATA_PATH = os.path.join(BASE_DIR, "data/india.json")

    def load_places_data():
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                places = json.load(f)
                return places
        except FileNotFoundError:
            print(f"Data file {DATA_PATH} not found.")
            return []
        except Exception as e:
            print(f"Error loading data file: {e}")
            return []
        
    places = load_places_data()

    # Prepare data for insertion with flattened metadata
    ids = [str(i) for i in range(len(places))]
    documents = [place["description"] for place in places]

    # Flatten metadata fields (e.g., convert lists to comma-separated strings)
    metadatas = []
    for place in places:
        flattened_metadata = {}
        for key, value in place.items():
            if isinstance(value, list):
                if isinstance(value[0], str):
                    flattend_value = ", ".join(value)
                elif isinstance(value[0], float):
                    flattend_value = ", ".join(map(str, value))
            else:
                flattend_value = value
            flattened_metadata[key] = flattend_value
        metadatas.append(flattened_metadata)
            
        
        

    embeddings = model.encode(documents).tolist()

    # Add to Chroma collection
    collection.upsert(documents=documents, metadatas=metadatas, embeddings=embeddings, ids=ids)
    print(f"Inserted {len(places)} places into Chroma collection.")
    results = query_places("beautiful historic monument in India", 5)
    for place in results:
        print(place["title"], "-", place["location"])