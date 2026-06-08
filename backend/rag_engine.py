import os
import chromadb
from chromadb.utils import embedding_functions

# Paths
BASE_DIR = "c:/Users/jatin/ragprojects/project_1/backend"
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "chromadb")
POLICY_FILE = os.path.join(DATA_DIR, "credit_card_agreement.txt")

# Initialize ChromaDB persistent client
# This stores the database on your hard drive so it doesn't vanish when the script stops.
chroma_client = chromadb.PersistentClient(path=DB_DIR)

# We use the SentenceTransformer embedding model "all-MiniLM-L6-v2"
# It translates text chunks into 384-dimensional dense vectors offline.
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def chunk_document(filepath):
    """
    Reads the credit card agreement and splits it into logical, readable chunks.
    We split by double newlines to keep paragraphs and bullet-point blocks intact.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Agreement file not found at {filepath}")
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by double newlines (paragraphs/sections)
    raw_chunks = content.split("\n\n")
    
    chunks = []
    current_section = "General"
    
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
            
        # Keep track of section headers to give context to our chunks
        if chunk.startswith("#"):
            current_section = chunk.replace("#", "").strip()
            
        chunks.append({
            "text": chunk,
            "metadata": {"section": current_section}
        })
        
    return chunks

def build_vector_store():
    """
    Reads the document chunks, embeds them, and saves them into the vector store.
    """
    print("--- Loading and Parsing Credit Card Agreement ---")
    chunks = chunk_document(POLICY_FILE)
    print(f"Generated {len(chunks)} text chunks.")
    
    # Get or create the collection
    # The collection uses our local SentenceTransformer model to embed incoming texts automatically.
    collection = chroma_client.get_or_create_collection(
        name="credit_card_policies",
        embedding_function=embedding_function
    )
    
    # Prepare data for ChromaDB
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    # Simple incremental IDs: doc_0, doc_1, ...
    ids = [f"doc_{i}" for i in range(len(chunks))]
    
    print("--- Indexing chunks into local ChromaDB (Vector DB) ---")
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print("ChromaDB indexing complete! Vectors saved to backend/chromadb/")

def query_policies(query_text, n_results=2):
    """
    Queries the vector database for policies semantically similar to the query.
    """
    # Load collection
    collection = chroma_client.get_collection(
        name="credit_card_policies",
        embedding_function=embedding_function
    )
    
    # Query collection
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    # Parse results into a clean list of matches
    matches = []
    if results["documents"]:
        for i in range(len(results["documents"][0])):
            matches.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0
            })
            
    return matches

if __name__ == "__main__":
    # If the database directory doesn't exist, create and index it
    # You can force index by running this script directly
    build_vector_store()
    
    # Let's perform a test query to verify our Semantic search works!
    test_queries = [
        "How long do I have to dispute an unauthorized charge?",
        "What is the penalty APR if I pay late?",
        "Do cash advances earn points?"
    ]
    
    print("\n--- Testing RAG Semantic Search ---")
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        matches = query_policies(q, n_results=1)
        for idx, match in enumerate(matches):
            print(f"Match (Score/Distance: {match['distance']:.4f}):")
            print(f"Section: {match['metadata'].get('section')}")
            print(f"Content:\n{match['text']}\n")
