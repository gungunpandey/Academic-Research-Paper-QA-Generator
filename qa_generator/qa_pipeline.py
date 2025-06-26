"""
QA Generation Pipeline - Main execution script
"""

import os
import json
import logging
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qa_generator.question_generator import QuestionGenerator
from qa_generator.config import QUESTION_CONFIG, OUTPUT_CONFIG
from src.google_sheets_client import GoogleSheetsClient

def setup_qa_logger():
    """Set up logging for QA generation"""
    log_dir = "qa_generator/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/qa_generation_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def load_processed_papers() -> List[Dict[str, Any]]:
    """
    Load processed papers from the results directory
    """
    papers = []
    results_dir = "results"
    
    if not os.path.exists(results_dir):
        logging.warning(f"Results directory not found: {results_dir}")
        return papers
    
    # Iterate through paper directories
    for paper_dir in os.listdir(results_dir):
        paper_path = os.path.join(results_dir, paper_dir)
        
        if os.path.isdir(paper_path):
            # Look for processed text chunks
            chunks_dir = os.path.join(paper_path, "processed_text", "chunks")
            
            if os.path.exists(chunks_dir):
                # Load all text chunks
                chunks = []
                for chunk_file in sorted(os.listdir(chunks_dir)):
                    if chunk_file.endswith('.txt'):
                        chunk_path = os.path.join(chunks_dir, chunk_file)
                        try:
                            with open(chunk_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content:
                                    chunks.append({
                                        "file": chunk_file,
                                        "content": content,
                                        "path": chunk_path
                                    })
                        except Exception as e:
                            logging.warning(f"Error reading chunk {chunk_file}: {e}")
                
                if chunks:
                    papers.append({
                        "paper_title": paper_dir,
                        "chunks": chunks,
                        "total_chunks": len(chunks)
                    })
                    logging.info(f"Loaded {len(chunks)} chunks for paper: {paper_dir}")
    
    return papers

def get_paper_metadata(paper_title: str) -> Dict[str, Any]:
    """
    Extract paper metadata from the title or other sources
    """
    # For now, we'll create basic metadata from the title
    # In a real implementation, you might load this from a database or file
    
    # Try to extract year from title (common pattern: "Title (2023)" or "Title 2023")
    import re
    year_match = re.search(r'\(?(\d{4})\)?', paper_title)
    year = year_match.group(1) if year_match else "Unknown"
    
    return {
        "paper_title": paper_title,
        "authors": "Unknown",  # Would need to be extracted from PDF or database
        "publication_year": year,
        "source": "processed_paper"
    }

def generate_qa_for_paper(question_generator: QuestionGenerator, 
                         paper_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate QA for a single paper
    """
    paper_title = paper_data["paper_title"]
    chunks = paper_data["chunks"]
    
    logging.info(f"Generating QA for paper: {paper_title}")
    
    # Extract content from chunks
    content_chunks = [chunk["content"] for chunk in chunks]
    
    # Get paper metadata
    metadata = get_paper_metadata(paper_title)
    
    # Generate questions
    questions = question_generator.generate_questions_for_paper(
        paper_metadata=metadata,
        content_chunks=content_chunks
    )
    
    # Save questions to JSON
    json_file = question_generator.save_questions_to_json(questions, paper_title)
    
    # Save to Google Sheets (if available)
    sheets_success = question_generator.save_questions_to_sheets(questions, paper_title)
    
    return {
        "paper_title": paper_title,
        "total_questions": len(questions),
        "json_file": json_file,
        "sheets_success": sheets_success,
        "questions": questions
    }

def main():
    """
    Main QA generation pipeline
    """
    logger = setup_qa_logger()
    logger.info("Starting QA Generation Pipeline")
    
    try:
        # Initialize question generator
        logger.info("Initializing question generator...")
        question_generator = QuestionGenerator(logger=logger)
        
        # Load processed papers
        logger.info("Loading processed papers...")
        papers = load_processed_papers()
        
        if not papers:
            logger.warning("No processed papers found. Please run the ingestion pipeline first.")
            return
        
        logger.info(f"Found {len(papers)} processed papers")
        
        # Generate QA for each paper
        results = []
        for i, paper_data in enumerate(papers):
            logger.info(f"Processing paper {i+1}/{len(papers)}: {paper_data['paper_title']}")
            
            try:
                result = generate_qa_for_paper(question_generator, paper_data)
                results.append(result)
                logger.info(f"Successfully generated {result['total_questions']} questions for {paper_data['paper_title']}")
                
            except Exception as e:
                logger.error(f"Error generating QA for {paper_data['paper_title']}: {e}")
                continue
        
        # Summary
        total_questions = sum(r['total_questions'] for r in results)
        logger.info(f"QA Generation Pipeline completed!")
        logger.info(f"Total papers processed: {len(results)}")
        logger.info(f"Total questions generated: {total_questions}")
        
        # Save summary report
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_papers": len(results),
            "total_questions": total_questions,
            "results": results
        }
        
        summary_file = f"qa_generator/output/qa_generation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Summary saved to: {summary_file}")
        
    except Exception as e:
        logger.error(f"Error in QA generation pipeline: {e}")
        raise

if __name__ == "__main__":
    main() 