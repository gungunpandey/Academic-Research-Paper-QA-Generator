"""
Configuration for QA Generation System
"""

# Free, Open-Source Models Configuration
MODEL_CONFIG = {
    # Primary model for question generation (Gemma-2B is free and performs well)
    "question_generation_model": "google/gemma-2b-it",  # Free, 2B parameters, good for instruction following
    
    # Alternative models (free and open source)
    "alternative_models": [
        "microsoft/DialoGPT-medium",  # Good for conversational QA
        "facebook/opt-350m",  # Smaller, faster alternative
        "EleutherAI/gpt-neo-125m",  # Lightweight option
    ],
    
    # Model settings
    "max_length": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "do_sample": True,
}

# Question Generation Parameters
QUESTION_CONFIG = {
    "questions_per_paper": 10,
    "question_types": [
        "multiple_choice",
        "short_answer", 
        "true_false",
        "fill_in_blank"
    ],
    
    # Bloom's Taxonomy levels
    "cognitive_levels": [
        "remember",
        "understand", 
        "apply",
        "analyze",
        "evaluate",
        "create"
    ],
    
    # Content categories
    "content_categories": [
        "methodology",
        "results",
        "conclusions",
        "background",
        "visual_content",
        "formulas"
    ]
}

# Output Configuration
OUTPUT_CONFIG = {
    "output_format": "json",
    "include_metadata": True,
    "include_explanations": True,
    "save_to_google_sheets": True,
    "google_sheet_name": "Research_Paper_QA_Questions"
}

# Prompt Templates
PROMPT_TEMPLATES = {
    "multiple_choice": """
    Generate a multiple choice question based on the following research content:
    
    Content: {content}
    
    Requirements:
    - Question should test understanding of key concepts
    - Provide 4 options (A, B, C, D)
    - Only one correct answer
    - Include explanation for the correct answer
    - Cognitive level: {cognitive_level}
    
    Format your response as JSON:
    {{
        "question": "Question text here?",
        "options": {{
            "A": "Option A",
            "B": "Option B", 
            "C": "Option C",
            "D": "Option D"
        }},
        "correct_answer": "A",
        "explanation": "Explanation for why this is correct",
        "cognitive_level": "{cognitive_level}",
        "content_category": "{content_category}"
    }}
    """,
    
    "short_answer": """
    Generate a short answer question based on the following research content:
    
    Content: {content}
    
    Requirements:
    - Question should require 2-3 sentence response
    - Include expected key points in explanation
    - Cognitive level: {cognitive_level}
    
    Format your response as JSON:
    {{
        "question": "Question text here?",
        "expected_answer": "Expected answer with key points",
        "explanation": "Detailed explanation of the answer",
        "cognitive_level": "{cognitive_level}",
        "content_category": "{content_category}"
    }}
    """,
    
    "true_false": """
    Generate a true/false question based on the following research content:
    
    Content: {content}
    
    Requirements:
    - Clear true/false statement
    - Include explanation for the answer
    - Cognitive level: {cognitive_level}
    
    Format your response as JSON:
    {{
        "question": "True or False: Statement here",
        "correct_answer": "True",
        "explanation": "Explanation for why this is true/false",
        "cognitive_level": "{cognitive_level}",
        "content_category": "{content_category}"
    }}
    """
}

# Error handling and fallbacks
ERROR_CONFIG = {
    "max_retries": 3,
    "fallback_model": "microsoft/DialoGPT-medium",
    "timeout_seconds": 30,
    "batch_size": 5
} 