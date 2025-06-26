"""
Question Generation Engine using Free, Open-Source Models
"""

import json
import logging
import random
import time
from typing import Dict, List, Optional, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from qa_generator.config import MODEL_CONFIG, QUESTION_CONFIG, PROMPT_TEMPLATES, ERROR_CONFIG
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.google_sheets_client import GoogleSheetsClient

class QuestionGenerator:
    """
    AI-powered question generation using free, open-source models
    """
    
    def __init__(self, credentials_path: str = 'credentials.json', logger: Optional[logging.Logger] = None):
        """
        Initialize the question generator with free models
        """
        self.logger = logger or logging.getLogger(__name__)
        self.credentials_path = credentials_path
        
        # Initialize models
        self.primary_model = None
        self.fallback_model = None
        self.tokenizer = None
        
        # Initialize Google Sheets client for QA output
        self.sheets_client = None
        self._initialize_models()
        self._initialize_sheets_client()
    
    def _initialize_models(self):
        """Initialize free, open-source models"""
        try:
            self.logger.info("Initializing question generation models...")
            
            # Try to load the primary model (Gemma-2B)
            try:
                model_name = MODEL_CONFIG["question_generation_model"]
                self.logger.info(f"Loading primary model: {model_name}")
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.primary_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float16,
                    device_map="auto" if torch.cuda.is_available() else "cpu"
                )
                
                # Add padding token if not present
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.logger.info("Primary model loaded successfully")
                
            except Exception as e:
                self.logger.warning(f"Failed to load primary model: {e}")
                self._load_fallback_model()
                
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
            raise
    
    def _load_fallback_model(self):
        """Load fallback model if primary fails"""
        try:
            fallback_name = ERROR_CONFIG["fallback_model"]
            self.logger.info(f"Loading fallback model: {fallback_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(fallback_name)
            self.fallback_model = AutoModelForCausalLM.from_pretrained(
                fallback_name,
                torch_dtype=torch.float16,
                device_map="auto" if torch.cuda.is_available() else "cpu"
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
            self.logger.info("Fallback model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load fallback model: {e}")
            raise
    
    def _initialize_sheets_client(self):
        """Initialize Google Sheets client for QA output"""
        try:
            from qa_generator.config import OUTPUT_CONFIG
            sheet_name = OUTPUT_CONFIG["google_sheet_name"]
            self.sheets_client = GoogleSheetsClient(
                credentials_path=self.credentials_path,
                sheet_name=sheet_name
            )
            self.logger.info(f"Google Sheets client initialized for: {sheet_name}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Google Sheets client: {e}")
            self.sheets_client = None
    
    def generate_question(self, content: str, question_type: str, cognitive_level: str, 
                         content_category: str) -> Optional[Dict[str, Any]]:
        """
        Generate a single question from content
        """
        try:
            # Get the appropriate prompt template
            if question_type not in PROMPT_TEMPLATES:
                self.logger.warning(f"Unknown question type: {question_type}")
                return None
            
            prompt = PROMPT_TEMPLATES[question_type].format(
                content=content[:1000],  # Limit content length
                cognitive_level=cognitive_level,
                content_category=content_category
            )
            
            # Generate response using the model
            model = self.primary_model or self.fallback_model
            if model is None or self.tokenizer is None:
                self.logger.error("No model or tokenizer available for question generation")
                return None
            
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, 
                                  max_length=MODEL_CONFIG["max_length"])
            
            # Generate response
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=MODEL_CONFIG["max_length"] + 200,
                    temperature=MODEL_CONFIG["temperature"],
                    top_p=MODEL_CONFIG["top_p"],
                    do_sample=MODEL_CONFIG["do_sample"],
                    pad_token_id=self.tokenizer.eos_token_id if self.tokenizer else None
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True) if self.tokenizer else ""
            
            # Extract the generated part (after the prompt)
            generated_text = response[len(prompt):].strip()
            
            # Try to parse JSON from the response
            try:
                # Find JSON in the response
                start_idx = generated_text.find('{')
                end_idx = generated_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != 0:
                    json_str = generated_text[start_idx:end_idx]
                    question_data = json.loads(json_str)
                    
                    # Add metadata
                    question_data.update({
                        "question_type": question_type,
                        "cognitive_level": cognitive_level,
                        "content_category": content_category,
                        "source_content": content[:200] + "..." if len(content) > 200 else content
                    })
                    
                    return question_data
                else:
                    self.logger.warning("No JSON found in model response")
                    return self._create_fallback_question(content, question_type, cognitive_level, content_category)
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from model response: {e}")
                return self._create_fallback_question(content, question_type, cognitive_level, content_category)
                
        except Exception as e:
            self.logger.error(f"Error generating question: {e}")
            return self._create_fallback_question(content, question_type, cognitive_level, content_category)
    
    def _create_fallback_question(self, content: str, question_type: str, 
                                cognitive_level: str, content_category: str) -> Dict[str, Any]:
        """
        Create a simple fallback question when model generation fails
        """
        if question_type == "multiple_choice":
            return {
                "question": f"What is the main topic discussed in this research content?",
                "options": {
                    "A": "Methodology",
                    "B": "Results", 
                    "C": "Background",
                    "D": "Conclusions"
                },
                "correct_answer": "A",
                "explanation": "This is a fallback question generated when the AI model failed.",
                "cognitive_level": cognitive_level,
                "content_category": content_category,
                "question_type": question_type,
                "source_content": content[:200] + "..." if len(content) > 200 else content,
                "is_fallback": True
            }
        elif question_type == "short_answer":
            return {
                "question": "Summarize the key findings of this research.",
                "expected_answer": "The research discusses important findings related to the topic.",
                "explanation": "This is a fallback question generated when the AI model failed.",
                "cognitive_level": cognitive_level,
                "content_category": content_category,
                "question_type": question_type,
                "source_content": content[:200] + "..." if len(content) > 200 else content,
                "is_fallback": True
            }
        else:  # true_false
            return {
                "question": "True or False: This research provides valuable insights.",
                "correct_answer": "True",
                "explanation": "This is a fallback question generated when the AI model failed.",
                "cognitive_level": cognitive_level,
                "content_category": content_category,
                "question_type": question_type,
                "source_content": content[:200] + "..." if len(content) > 200 else content,
                "is_fallback": True
            }
    
    def generate_questions_for_paper(self, paper_metadata: Dict[str, Any], 
                                   content_chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Generate multiple questions for a research paper
        """
        questions = []
        questions_per_paper = QUESTION_CONFIG["questions_per_paper"]
        
        self.logger.info(f"Generating {questions_per_paper} questions for paper: {paper_metadata.get('paper_title', 'Unknown')}")
        
        # Distribute questions across different types and cognitive levels
        question_distribution = self._create_question_distribution(questions_per_paper)
        
        for i, (question_type, cognitive_level, content_category) in enumerate(question_distribution):
            # Select content chunk for this question
            content_chunk = content_chunks[i % len(content_chunks)]
            
            # Generate question
            question_data = self.generate_question(
                content=content_chunk,
                question_type=question_type,
                cognitive_level=cognitive_level,
                content_category=content_category
            )
            
            if question_data:
                # Add paper metadata
                question_data.update({
                    "paper_title": paper_metadata.get("paper_title", ""),
                    "authors": paper_metadata.get("authors", ""),
                    "publication_year": paper_metadata.get("publication_year", ""),
                    "question_id": f"q_{i+1:03d}",
                    "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                questions.append(question_data)
                self.logger.info(f"Generated question {i+1}/{questions_per_paper}")
            
            # Add small delay to avoid overwhelming the model
            time.sleep(0.5)
        
        return questions
    
    def _create_question_distribution(self, total_questions: int) -> List[tuple]:
        """
        Create a balanced distribution of question types and cognitive levels
        """
        distribution = []
        
        question_types = QUESTION_CONFIG["question_types"]
        cognitive_levels = QUESTION_CONFIG["cognitive_levels"]
        content_categories = QUESTION_CONFIG["content_categories"]
        
        for i in range(total_questions):
            question_type = question_types[i % len(question_types)]
            cognitive_level = cognitive_levels[i % len(cognitive_levels)]
            content_category = content_categories[i % len(content_categories)]
            
            distribution.append((question_type, cognitive_level, content_category))
        
        # Shuffle to add variety
        random.shuffle(distribution)
        return distribution
    
    def save_questions_to_json(self, questions: List[Dict[str, Any]], 
                              paper_title: str) -> str:
        """
        Save questions to JSON file
        """
        output_dir = "qa_generator/output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize filename
        safe_title = "".join(c for c in paper_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        
        filename = f"{output_dir}/{safe_title}_questions.json"
        
        output_data = {
            "paper_metadata": {
                "title": paper_title,
                "total_questions": len(questions),
                "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "questions": questions
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Questions saved to: {filename}")
        return filename
    
    def save_questions_to_sheets(self, questions: List[Dict[str, Any]], 
                                paper_title: str) -> bool:
        """
        Save questions to Google Sheets
        """
        if not self.sheets_client:
            self.logger.warning("Google Sheets client not available")
            return False
        
        try:
            # Prepare data for sheets
            sheet_data = []
            for question in questions:
                row = {
                    "paper_title": question.get("paper_title", ""),
                    "question_id": question.get("question_id", ""),
                    "question_type": question.get("question_type", ""),
                    "cognitive_level": question.get("cognitive_level", ""),
                    "content_category": question.get("content_category", ""),
                    "question_text": question.get("question", ""),
                    "options": json.dumps(question.get("options", {})) if question.get("options") else "",
                    "correct_answer": question.get("correct_answer", question.get("expected_answer", "")),
                    "explanation": question.get("explanation", ""),
                    "generation_timestamp": question.get("generation_timestamp", "")
                }
                sheet_data.append(row)
            
            # Add to sheets (this would need to be implemented in the sheets client)
            # For now, we'll just log the data
            self.logger.info(f"Prepared {len(sheet_data)} questions for Google Sheets")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to Google Sheets: {e}")
            return False 