import os
import json
import uuid
import re
import logging
import datetime
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import pandas as pd
from tqdm import tqdm
import textwrap

# Adjusting path to import from the 'src' directory
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from google_sheets_client import GoogleSheetsClient
from paper_processor import ResearchPaperProcessor

def setup_paper_logger(paper_title):
    """Sets up a specific logger for a paper that logs to a file with unique ID."""
    sanitized_title = re.sub(r'[^a-zA-Z0-9_ -]', '', paper_title).replace(' ', '_')
    log_dir = os.path.join('results', sanitized_title, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create unique log file name with timestamp and UUID
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    log_file = os.path.join(log_dir, f'processing_{timestamp}_{unique_id}.log')

    logger = logging.getLogger(f"{sanitized_title}_{unique_id}")
    logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # File handler
    handler = logging.FileHandler(log_file, mode='w')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger, sanitized_title, log_file

def get_image_embedding_model():
    """Initialize and return an image embedding model (CLIP)."""
    try:
        from sentence_transformers import SentenceTransformer
        # For now, use the same text embedding model for images to ensure dimension compatibility
        # This will use the text model to encode image captions/descriptions instead of raw images
        # TODO: Find a proper 384-dimensional image embedding model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except ImportError:
        print("Warning: SentenceTransformer not available. Install with: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"Warning: Could not load embedding model: {e}")
        return None

def embed_image(image_path, image_model):
    """Generate embedding for an image using its description/caption."""
    try:
        # Since we're using a text embedding model, we'll create a text description
        # based on the image path and any available metadata
        image_filename = os.path.basename(image_path)
        
        # Create a descriptive text for the image
        # This is a simple approach - in a real implementation, you might want to
        # extract actual captions from the PDF or use OCR to describe the image
        image_description = f"Figure or image from research paper: {image_filename}"
        
        # Generate embedding using the text model
        embedding = image_model.encode(image_description)
        
        if hasattr(embedding, 'tolist'):
            return embedding.tolist()
        else:
            import numpy as np
            return np.array(embedding).tolist()
            
    except Exception as e:
        print(f"Error embedding image {image_path}: {e}")
        return None

def save_processed_text_page_wise(sanitized_title, pdf_path, text_splitter_config, logger):
    """Saves cleaned text page by page for better understanding."""
    import fitz  # PyMuPDF
    
    base_dir = os.path.join('results', sanitized_title, 'processed_text')
    pages_dir = os.path.join(base_dir, 'pages')
    chunks_dir = os.path.join(base_dir, 'chunks')
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(chunks_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    page_chunks = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Use get_text('text') for compatibility
        try:
            page_text = page.get_text('text')
        except Exception:
            page_text = page.get_text()
        # Clean and format page text
        cleaned_text = ' '.join(page_text.split())  # Remove excessive whitespace
        wrapped_text = '\n'.join(textwrap.wrap(cleaned_text, width=120))
        
        if wrapped_text.strip():  # Only save non-empty pages
            page_filename = f"page_{page_num + 1:03d}.txt"
            page_path = os.path.join(pages_dir, page_filename)
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(f"Page {page_num + 1}\n")
                f.write("=" * 50 + "\n")
                f.write(wrapped_text)
                f.write("\n")
            # Also create chunks for vector storage
            page_chunks.extend(clean_and_chunk_text(cleaned_text, text_splitter_config))
    doc.close()
    num_pages = page_num + 1
    # Save combined chunks for vector storage
    for i, chunk in enumerate(page_chunks):
        chunk_filename = f"chunk_{i+1:03d}.txt"
        chunk_path = os.path.join(chunks_dir, chunk_filename)
        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(chunk)
    logger.info(f"Saved {num_pages} pages to {pages_dir} and {len(page_chunks)} chunks to {chunks_dir}")
    return page_chunks

def clean_and_chunk_text(text, text_splitter_config):
    """Cleans and chunks the text."""
    # Basic cleaning
    text = text.replace("\n", " ").strip()
    # Simple chunking (can be replaced with more sophisticated methods)
    chunk_size = text_splitter_config['chunk_size']
    chunk_overlap = text_splitter_config['chunk_overlap']
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        if start >= len(text):
            break
            
    return chunks

def ingest_pipeline():
    """
    Main ingestion pipeline that reads from Google Sheets and processes papers.
    """
    # 1. Load Configuration and Secrets
    load_dotenv()
    with open('config.json', 'r') as f:
        config = json.load(f)

    QDRANT_URI = os.getenv("QDRANT_URI")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    SHEET_NAME = config['google_sheet_name']
    COLLECTION_NAME = config['collection_name']

    if SHEET_NAME == "YOUR_GOOGLE_SHEET_NAME":
        print("FATAL: Please set your Google Sheet name in config.json")
        return

    # 2. Initialize Clients
    try:
        sheets_client = GoogleSheetsClient(credentials_path='credentials.json', sheet_name=SHEET_NAME)
        qdrant_client = QdrantClient(url=QDRANT_URI, api_key=QDRANT_API_KEY, timeout=60)
        text_embedding_model = SentenceTransformer(config['embedding_model_name'])
        image_embedding_model = get_image_embedding_model()
        paper_processor = ResearchPaperProcessor(config)
    except Exception as e:
        print(f"Failed to initialize clients: {e}")
        return

    # 3. Get Paper Queue from Google Sheets
    papers_df = sheets_client.get_all_records_as_df()
    # Only process rows where both statuses are empty
    papers_to_process = papers_df[(papers_df['ingestion_status'] == '') & (papers_df['extraction_status'] == '')]

    if papers_to_process.empty:
        print("All papers in the Google Sheet have been processed. No new papers to ingest.")
        return
        
    print(f"Found {len(papers_to_process)} paper(s) to process.")

    # 4. Process Each Paper
    for index, paper_row in papers_to_process.iterrows():
        # The DataFrame index is 0-based. Google Sheet rows are 1-based, plus 1 for the header.
        sheet_row_index = index + 2
        paper_title = paper_row['paper_title']
        
        logger, sanitized_title, log_file = setup_paper_logger(paper_title)
        
        try:
            logger.info(f"--- Processing paper: {paper_title} ---")
            logger.info(f"Log file: {log_file}")
            
            paper_metadata = {k: paper_row[k] for k in ['paper_title', 'authors', 'publication_year']}
            
            # Update both ingestion and extraction status to "In Progress"
            sheets_client.update_status(sheet_row_index, 'ingestion_status', 'In Progress')
            sheets_client.update_status(sheet_row_index, 'extraction_status', 'In Progress')

            # Initialize processor with this paper's logger
            paper_processor = ResearchPaperProcessor(config, logger)
            raw_text, formulas = paper_processor.process_paper(paper_row['paper_path'])
            
            # Save text page-wise and get chunks for vector storage
            text_chunks = save_processed_text_page_wise(sanitized_title, paper_row['paper_path'], config['text_splitter'], logger)

            # Extract images only (no tables)
            visuals_dir = os.path.join('results', sanitized_title, 'visuals')
            images_metadata = paper_processor.extract_visuals(paper_row['paper_path'], visuals_dir)
            
            # Save images metadata as JSON
            with open(os.path.join(visuals_dir, 'images_metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(images_metadata, f, indent=2)
            
            logger.info(f"Extracted {len(images_metadata)} images to {visuals_dir}")
            
            # Prepare documents for ingestion
            documents = []
            
            # Add text chunks
            logger.info(f"Preparing {len(text_chunks)} text chunks for embedding...")
            for chunk in text_chunks:
                documents.append({"type": "text", "content": chunk, **paper_metadata})
            
            # Add formulas
            logger.info(f"Preparing {len(formulas)} formulas for embedding...")
            for formula in formulas:
                documents.append({"type": "formula", "content": formula['content'], **paper_metadata})
            
            # Add images (if image embedding model is available)
            if image_embedding_model and images_metadata:
                logger.info(f"Preparing {len(images_metadata)} images for embedding...")
                for img_meta in images_metadata:
                    img_path = img_meta['path']
                    if os.path.exists(img_path):
                        documents.append({
                            "type": "image", 
                            "content": img_path,  # Store path for embedding
                            "page": img_meta['page'],
                            "caption": img_meta.get('caption', ''),
                            **paper_metadata
                        })

            logger.info(f"Created {len(documents)} documents for ingestion ({len(text_chunks)} text chunks, {len(formulas)} formulas, {len(images_metadata)} images).")

            # Generate embeddings and prepare points for Qdrant
            points_to_ingest = []
            
            logger.info("Starting embedding generation...")
            for i, doc in enumerate(tqdm(documents, desc="Generating embeddings")):
                try:
                    if doc['type'] == 'image':
                        # Generate image embedding
                        if image_embedding_model:
                            vector = embed_image(doc['content'], image_embedding_model)
                            if vector:
                                points_to_ingest.append(models.PointStruct(
                                    id=str(uuid.uuid4()), 
                                    vector=vector, 
                                    payload=doc
                                ))
                            else:
                                logger.warning(f"Failed to generate embedding for image: {doc['content']}")
                        else:
                            logger.warning("Image embedding model not available, skipping image")
                    else:
                        # Generate text embedding
                        vector = text_embedding_model.encode(doc['content'])
                        if hasattr(vector, 'tolist'):
                            vector = vector.tolist()
                        else:
                            import numpy as np
                            vector = np.array(vector).tolist()
                        points_to_ingest.append(models.PointStruct(
                            id=str(uuid.uuid4()), 
                            vector=vector, 
                            payload=doc
                        ))
                except Exception as e:
                    logger.error(f"Error generating embedding for document {i}: {e}")
                    continue
            
            logger.info(f"Generated {len(points_to_ingest)} embeddings successfully")
            
            # Ingest to Qdrant
            if points_to_ingest:
                logger.info(f"Ingesting {len(points_to_ingest)} points to Qdrant collection: {COLLECTION_NAME}")
                qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points_to_ingest, wait=True)
                logger.info(f"Successfully ingested {len(points_to_ingest)} points to Qdrant")
            else:
                logger.warning("No points to ingest")
            
            # Update both statuses to "Completed"
            sheets_client.update_status(sheet_row_index, 'ingestion_status', 'Completed')
            sheets_client.update_status(sheet_row_index, 'extraction_status', 'Completed')
            sheets_client.update_status(sheet_row_index, 'notes', f'Ingestion successful. Extracted {len(formulas)} formulas, {len(text_chunks)} text chunks, {len(images_metadata)} images.')

        except Exception as e:
            logger.error(f"Failed to process paper '{paper_title}'. Reason: {e}", exc_info=True)
            sheets_client.update_status(sheet_row_index, 'ingestion_status', 'Failed')
            sheets_client.update_status(sheet_row_index, 'extraction_status', 'Failed')
            sheets_client.update_status(sheet_row_index, 'notes', str(e))
            continue

    logger.info("--- Ingestion pipeline finished! ---")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    ingest_pipeline() 