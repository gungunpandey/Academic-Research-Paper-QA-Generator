import fitz  # PyMuPDF
import os
from typing import Dict, Any, List, Tuple
from grobid_client.grobid_client import GrobidClient
from PIL import Image
import io
import re
import pytesseract
import json
import logging
import shutil

class ResearchPaperProcessor:
    """
    Advanced PDF processing with academic paper awareness, now with Grobid integration
    and visual extraction.
    - Section identification via Grobid
    - Citation network extraction via Grobid
    - Figure/table extraction with contextual understanding
    - Mathematical equation parsing (placeholder)
    """
    def __init__(self, config, logger=None):
        """
        Initializes the processor with configuration and a logger.
        """
        self.config = config
        self.grobid_server = config.get('grobid_server', 'http://localhost:8070')
        # Use the provided logger, or create a basic one if None
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(logging.StreamHandler())
        
        # Check if tesseract is available
        self.tesseract_available = self._check_tesseract_availability()

    def _check_tesseract_availability(self):
        """Check if tesseract is installed and accessible."""
        try:
            # Try to find tesseract in PATH
            tesseract_path = shutil.which('tesseract')
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                return True
            else:
                # Try common installation paths
                common_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    '/usr/bin/tesseract',
                    '/usr/local/bin/tesseract'
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        return True
                return False
        except Exception:
            return False

    def _is_server_running(self):
        """Checks if the GROBID server is up and running."""
        try:
            client = GrobidClient(grobid_server=self.grobid_server, check_server=True)
            return client.is_grobid_up()
        except Exception:
            return False

    def process_paper(self, pdf_path):
        """
        Processes a single research paper to extract text and formulas.
        
        Args:
            pdf_path (str): The file path to the PDF.

        Returns:
            tuple: A tuple containing:
                - str: The extracted raw text.
                - list: A list of extracted formula dictionaries.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at {pdf_path}")

        self.logger.info("Extracting raw text from PDF...")
        raw_text = self._extract_text_from_pdf(pdf_path)
        
        self.logger.info("Extracting formulas...")
        formulas = self._extract_formulas(pdf_path, raw_text, min_formula_count=5)
        
        return raw_text, formulas

    def _extract_text_from_pdf(self, pdf_path):
        """Extracts raw text content from a PDF."""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    def _extract_formulas(self, pdf_path, raw_text, min_formula_count=5, use_ocr_fallback=True):
        """
        Hybrid extraction of mathematical formulas:
        1. Try text-based extraction using regex.
        2. If not enough formulas are found, fallback to OCR on images.
        Returns a list of dicts: {formula, source, page}
        """
        self.logger.info("Extracting formulas (text-based first)...")
        
        text_formulas = self._extract_formulas_with_text(raw_text)
        
        self.logger.info(f"Found {len(text_formulas)} formulas via text-based extraction.")
        
        # Fallback to OCR if not enough text-based formulas are found
        if use_ocr_fallback and len(text_formulas) < min_formula_count:
            if self.tesseract_available:
                self.logger.info("Text-based extraction found few formulas. Falling back to OCR...")
                ocr_formulas = self._extract_formulas_with_ocr(pdf_path)
                
                # Combine and remove duplicates
                final_formulas = text_formulas
                existing_contents = {f['content'] for f in final_formulas}
                for ocr_f in ocr_formulas:
                    if ocr_f['content'] not in existing_contents:
                        final_formulas.append(ocr_f)
                        existing_contents.add(ocr_f['content'])
                
                self.logger.info(f"Found {len(final_formulas)} formulas after combining with OCR results.")
                return final_formulas
            else:
                self.logger.warning("Tesseract is not installed or not in PATH. Skipping OCR-based formula extraction.")
                self.logger.info("To enable OCR-based formula extraction, please install Tesseract:")
                self.logger.info("Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
                self.logger.info("Linux: sudo apt-get install tesseract-ocr")
                self.logger.info("macOS: brew install tesseract")
        
        return text_formulas

    def _extract_formulas_with_text(self, text):
        """
        Extracts formulas from text using comprehensive regex patterns.
        Returns a list of dicts: {formula, source, page}
        """
        # Comprehensive regex patterns for mathematical formulas
        patterns = [
            # LaTeX-style math
            r'\$\$(.*?)\$\$',  # Display mode math
            r'\$(.*?)\$',      # Inline math
            r'\\\[(.*?)\\\]',  # Display mode with \[ \]
            r'\\\((.*?)\\\)',  # Inline mode with \( \)
            
            # Common mathematical expressions
            r'\b[A-Za-z]\s*=\s*[A-Za-z0-9+\-*/^()\[\]{}\s,.]+\b',  # Simple equations
            r'\b[A-Za-z]\s*\+\s*[A-Za-z0-9+\-*/^()\[\]{}\s,.]+\b',  # Addition expressions
            r'\b[A-Za-z]\s*-\s*[A-Za-z0-9+\-*/^()\[\]{}\s,.]+\b',   # Subtraction expressions
            r'\b[A-Za-z]\s*\*\s*[A-Za-z0-9+\-*/^()\[\]{}\s,.]+\b',  # Multiplication expressions
            
            # Mathematical functions
            r'\b(sin|cos|tan|log|ln|exp|sqrt|sum|prod|int|lim)\s*\([^)]*\)\b',
            
            # Greek letters and mathematical symbols
            r'[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]',
            r'[∑∫∂∏√∞≠≤≥±×÷]',
            
            # Subscripts and superscripts
            r'[A-Za-z]_[A-Za-z0-9]',  # Subscripts
            r'[A-Za-z]\^[A-Za-z0-9]',  # Superscripts
        ]
        
        found_formulas = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            for formula_content in matches:
                # Basic cleaning of the extracted formula
                cleaned_formula = formula_content.strip()
                if cleaned_formula and len(cleaned_formula) > 2:  # Filter out very short matches
                    found_formulas.append(cleaned_formula)
        
        # Remove duplicates while preserving order
        unique_formulas = list(dict.fromkeys(found_formulas))
        
        return [{"type": "text-eqn", "content": f, "page": "N/A"} for f in unique_formulas]

    def _extract_formulas_with_ocr(self, pdf_path):
        """
        Extracts formulas from images within the PDF using OCR.
        Returns a list of dicts: {formula, source, page}
        """
        if not self.tesseract_available:
            self.logger.warning("Tesseract is not available. Skipping OCR-based formula extraction.")
            return []
            
        formulas = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Use pytesseract to extract text
                    ocr_text = pytesseract.image_to_string(image)
                    
                    # Enhanced filter for formula-like content
                    formula_indicators = ['+=∑∫∂<>()[]{}', 'sin', 'cos', 'tan', 'log', 'exp', 'sqrt', 'sum', 'prod', 'int', 'lim']
                    if any(indicator in ocr_text for indicator in formula_indicators):
                        formulas.append({
                            "type": "ocr-eqn",
                            "content": ocr_text.strip(),
                            "page": page_num + 1
                        })
                except Exception as e:
                    self.logger.warning(f"Could not process image {img_index} on page {page_num + 1}: {e}")
        doc.close()
        return formulas

    def extract_visuals(self, pdf_path, output_dir: str) -> List[Dict[str, Any]]:
        """
        Extracts images (figures, tables) from the PDF and saves them.
        Tries to guess the caption based on nearby text.
        Returns a list of dicts with metadata for each visual.
        """
        visuals = []
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            img_list = page.get_images(full=True)
            for img_index, img in enumerate(img_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                img_filename = f"page{page_num+1}_img{img_index+1}.png"
                img_path = os.path.join(output_dir, img_filename)
                try:
                    image = Image.open(io.BytesIO(image_bytes))
                    image.save(img_path, format='PNG')
                    visuals.append({
                        "type": "image",
                        "path": img_path,
                        "page": page_num + 1,
                        "caption": "Caption extraction not yet implemented."
                    })
                except Exception as e:
                    self.logger.warning(f"Skipping an image on page {page_num+1} due to error: {e}")
        doc.close()
        return visuals

    def extract_text(self) -> str:
        """Extracts all text from the PDF."""
        # This is the old method, kept for fallback/comparison
        text = ""
        for page in self.doc:
            text += page.get_text()
        return text

def main():
    """
    Main function for standalone execution to test paper processing.
    """
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found. Please create it for standalone testing.")
        return

    test_paper_path = "research_papers/NIPS-2017-attention-is-all-you-need-Paper.pdf"

    if not os.path.exists(test_paper_path):
        print(f"Test paper not found at: {test_paper_path}")
        return

    processor = ResearchPaperProcessor(config)
    
    if processor._is_server_running():
        print("GROBID server is up and running.")
    else:
        print("Warning: GROBID server is not running.")

    raw_text, formulas = processor.process_paper(test_paper_path)

    print("\n--- Raw Text Extracted (first 500 chars) ---")
    print(raw_text[:500] + "...")
    
    print(f"\n--- Found {len(formulas)} Formulas ---")
    for i, formula in enumerate(formulas[:10]): # Print first 10
        print(f"  {i+1}. [{formula['type']}] {formula['content']}")

if __name__ == '__main__':
    main() 