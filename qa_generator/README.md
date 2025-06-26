# QA Generation Module

This module implements the question generation engine for the Academic Research Paper Q&A Generator system.

## 🎯 Overview

The QA Generation module uses free, open-source language models to automatically generate questions from processed research paper content. It supports multiple question types and cognitive levels based on Bloom's Taxonomy.

## 🚀 Features

- **Free, Open-Source Models**: Uses Google's Gemma-2B and other free models
- **Multiple Question Types**: MCQ, Short Answer, True/False, Fill-in-the-Blank
- **Bloom's Taxonomy Integration**: Questions across all 6 cognitive levels
- **JSON Output**: Structured question data with metadata
- **Google Sheets Integration**: Export questions to spreadsheets
- **Fallback System**: Robust error handling with backup models

## 📁 Structure

```
qa_generator/
├── config.py              # Configuration settings
├── question_generator.py  # Main question generation engine
├── qa_pipeline.py         # Complete QA generation pipeline
├── test_qa_generation.py  # Test script
├── models/                # Model storage (if needed)
├── output/                # Generated questions (JSON files)
└── logs/                  # Generation logs
```

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Download Models** (automatic on first run):
   - Google Gemma-2B (primary model)
   - Microsoft DialoGPT-medium (fallback)
   - Facebook OPT-350M (alternative)

## 🎮 Usage

### Quick Test
```bash
cd qa_generator
python test_qa_generation.py
```

### Generate QA for All Processed Papers
```bash
python qa_pipeline.py
```

### Custom Question Generation
```python
from qa_generator.question_generator import QuestionGenerator

# Initialize generator
generator = QuestionGenerator()

# Generate a question
question = generator.generate_question(
    content="Your research content here...",
    question_type="multiple_choice",
    cognitive_level="understand",
    content_category="methodology"
)
```

## 📊 Output Format

### JSON Structure
```json
{
  "paper_metadata": {
    "title": "Paper Title",
    "total_questions": 10,
    "generation_timestamp": "2025-06-26 12:30:45"
  },
  "questions": [
    {
      "question_id": "q_001",
      "question_type": "multiple_choice",
      "cognitive_level": "understand",
      "content_category": "methodology",
      "question": "What is the main innovation of the Transformer architecture?",
      "options": {
        "A": "Self-attention mechanisms",
        "B": "Recurrent connections",
        "C": "Convolutional layers",
        "D": "Pooling operations"
      },
      "correct_answer": "A",
      "explanation": "The Transformer relies entirely on self-attention mechanisms...",
      "paper_title": "Attention Is All You Need",
      "authors": "Unknown",
      "publication_year": "2017",
      "generation_timestamp": "2025-06-26 12:30:45"
    }
  ]
}
```

## ⚙️ Configuration

### Model Settings (`config.py`)
- **Primary Model**: `google/gemma-2b-it`
- **Fallback Models**: DialoGPT, OPT, GPT-Neo
- **Generation Parameters**: Temperature, Top-p, Max length

### Question Settings
- **Questions per Paper**: 10 (configurable)
- **Question Types**: Multiple choice, Short answer, True/False
- **Cognitive Levels**: Remember, Understand, Apply, Analyze, Evaluate, Create
- **Content Categories**: Methodology, Results, Conclusions, Background, Visual content, Formulas

## 🔧 Customization

### Adding New Question Types
1. Add template to `PROMPT_TEMPLATES` in `config.py`
2. Update `QUESTION_CONFIG["question_types"]`
3. Add handling in `QuestionGenerator.generate_question()`

### Using Different Models
1. Update `MODEL_CONFIG["question_generation_model"]`
2. Add model to `alternative_models` list
3. Ensure model supports text generation

## 🐛 Troubleshooting

### Model Loading Issues
- **CUDA Memory**: Use CPU if GPU memory insufficient
- **Model Download**: Check internet connection for model downloads
- **Fallback**: System automatically uses backup models

### Question Generation Issues
- **JSON Parsing**: Check model output format
- **Content Length**: Truncate long content if needed
- **Fallback Questions**: Generated when model fails

### Google Sheets Issues
- **Credentials**: Ensure `credentials.json` is properly configured
- **Sheet Name**: Check `OUTPUT_CONFIG["google_sheet_name"]`
- **Permissions**: Verify Google Sheets API access

## 📈 Performance

- **Generation Speed**: ~2-5 seconds per question
- **Model Size**: Gemma-2B (~4GB RAM)
- **Batch Processing**: 5 questions per batch
- **Fallback Rate**: <5% (automatic fallback questions)

## 🔮 Future Enhancements

- **Visual Question Generation**: Questions from figures and diagrams
- **Cross-Paper Questions**: Synthesis across multiple papers
- **Difficulty Calibration**: Adaptive question complexity
- **Answer Validation**: Automated answer checking
- **Multi-Language Support**: Questions in different languages

## 📝 Notes

- Models are downloaded automatically on first use
- Generated questions include metadata for tracking
- Fallback questions ensure system reliability
- All models used are free and open-source
- Output is compatible with existing document processing pipeline 