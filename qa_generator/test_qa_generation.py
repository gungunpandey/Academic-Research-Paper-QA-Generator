"""
Test script for QA Generation System
"""

import json
import logging
from qa_generator.question_generator import QuestionGenerator
from qa_generator.config import QUESTION_CONFIG

def test_qa_generation():
    """
    Test the QA generation with sample content
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Sample research content for testing
    sample_content = """
    Attention Is All You Need introduces the Transformer architecture, which relies entirely on self-attention mechanisms 
    to compute representations of its input and output without using sequence-aligned RNNs or convolution. The Transformer 
    achieves state-of-the-art results in machine translation tasks and can be parallelized significantly more than RNNs 
    or CNNs. The model uses an encoder-decoder architecture where the encoder maps an input sequence of symbol 
    representations to a sequence of continuous representations. The decoder then generates an output sequence of symbols 
    one element at a time, using the encoder output and previously generated symbols as input.
    
    The key innovation of the Transformer is the multi-head self-attention mechanism, which allows the model to jointly 
    attend to information from different representation subspaces at different positions. This mechanism enables the model 
    to capture long-range dependencies more effectively than RNNs and CNNs. The Transformer also uses positional 
    encodings to inject information about the relative or absolute position of tokens in the sequence.
    """
    
    try:
        logger.info("Initializing Question Generator...")
        generator = QuestionGenerator(logger=logger)
        
        logger.info("Testing question generation...")
        
        # Test different question types
        question_types = ["multiple_choice", "short_answer", "true_false"]
        
        for question_type in question_types:
            logger.info(f"Testing {question_type} question generation...")
            
            question = generator.generate_question(
                content=sample_content,
                question_type=question_type,
                cognitive_level="understand",
                content_category="methodology"
            )
            
            if question:
                logger.info(f"Generated {question_type} question:")
                logger.info(f"Question: {question.get('question', 'N/A')}")
                if question.get('options'):
                    logger.info(f"Options: {question.get('options')}")
                logger.info(f"Answer: {question.get('correct_answer', question.get('expected_answer', 'N/A'))}")
                logger.info(f"Explanation: {question.get('explanation', 'N/A')}")
                logger.info("-" * 50)
            else:
                logger.warning(f"Failed to generate {question_type} question")
        
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    test_qa_generation() 