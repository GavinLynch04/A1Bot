import json
import os
import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer

METADATA_FILE = "./Documents/processed_pdfs.json"

embedder = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="../knowledge/rag_database")
collection = chroma_client.get_or_create_collection(name="firstaid_knowledge")

class KnowledgeBase:
    def __init__(self):
        """
        Initializes the knowledge base with empty datasets for terrain, weather,
        resources, and chat history.
        """
        self.data = {
            "rescuee_location": "Location Data: ",
            "rescue_weather": "Weather Data: ",
            "rescuee_condition": "Rescuee Condition: ",
            "other_data": "Other Relevant Data: ",
        }
        self.lat = None
        self.lon = None
        self.nearest_hospital = None
        self.weather = ''
        self.chat_history = []

    # Searches through chromaDB for relevant information
    def retrieve_relevant_text(self, input, top_k=1):
        query_embedding = embedder.encode([input]).tolist()[0]
        results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

        # Return the first set of retrieved documents if available
        return str(results['documents'][0]) if results.get('documents') else ""


"""Everything below is for generating the ChromaDB database from selected PDFs.
Nothing below should need to be run, database should be already created."""
def load_processed_pdfs():
    """Load the list of processed PDFs from a JSON file."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_processed_pdfs(processed_pdfs):
    """Save the list of processed PDFs to a JSON file."""
    with open(METADATA_FILE, "w") as f:
        json.dump(processed_pdfs, f, indent=4)

def process_text(text, source_name):
    """Splits text into chunks, embeds them, and stores them in ChromaDB with overlap."""
    chunks = [text[i:i + 500] for i in range(0, len(text), 100)]
    embeddings = embedder.encode(chunks).tolist()

    # Get existing document IDs in ChromaDB
    existing_ids = set(
        collection.get(ids=[f"{source_name}-{i}" for i in range(len(chunks))]).get("ids", [])
    )

    for i, chunk in enumerate(chunks):
        chunk_id = f"{source_name}-{i}"
        if chunk_id in existing_ids:
            continue
        collection.add(
            ids=[chunk_id],
            documents=[chunk],
            embeddings=[embeddings[i]]
        )

def process_pdf(pdf_path, processed_pdfs):
    """Extracts text from a PDF and stores it in ChromaDB."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    if text.strip():
        process_text(text, os.path.basename(pdf_path))
        processed_pdfs[os.path.basename(pdf_path)] = True
        save_processed_pdfs(processed_pdfs)


if __name__ == "__main__":
    processed_pdfs = load_processed_pdfs()
    for root, _, files in os.walk("./Documents"):
        for file in files:
            if file.endswith(".pdf") and file not in processed_pdfs:
                pdf_path = os.path.join(root, file)
                print(f"Processing new PDF: {pdf_path}")
                process_pdf(pdf_path, processed_pdfs)
            else:
                print(f"Skipping already processed PDF: {file}")
