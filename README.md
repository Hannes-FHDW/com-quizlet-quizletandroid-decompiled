# Quizlet Learning Algorithm Reimplementation

This repository contains a comprehensive reimplementation of Quizlet's learning algorithm based on analysis of the decompiled Android app. The implementation focuses on the core learning mechanics including text sanitization, question type selection, spaced repetition, and progress tracking.

## Overview

The reimplementation includes the key components identified from the Quizlet app:

### 1. Text Sanitization & Answer Validation (`TextSanitizer`)
- **Character Normalization**: Converts smart quotes, accents, and special characters to standard forms
- **Punctuation Removal**: Removes punctuation while preserving word structure  
- **Spell Checking**: Uses Levenshtein distance with configurable tolerance for spelling errors
- **Case Normalization**: Converts to lowercase for comparison
- **Whitespace Handling**: Normalizes multiple spaces and trims whitespace

Based on analysis of:
- `grading/core/` - Core grading logic
- `grading/impls/` - Text normalization implementations  
- `util/b.java` - Character normalization mappings
- `grading/impls/levenshteinplus/` - Spelling tolerance logic

### 2. Question Type System (`QuestionType`)
Supports multiple question types with adaptive selection:
- **WRITTEN**: Text input questions (hardest)
- **MULTIPLE_CHOICE**: 4-option multiple choice
- **TRUE_FALSE**: True/false questions
- **FILL_IN_BLANK**: Fill-in-the-blank questions
- **REVEAL_SELF_ASSESSMENT**: Self-assessment questions

Question type selection is based on learner confidence:
- Low confidence (< 0.3): Multiple choice questions
- Medium confidence (0.3-0.6): Mix of multiple choice and fill-in-blank
- High confidence (> 0.6): Written answer questions

### 3. Learning Algorithm (`LearningAlgorithm`)
Implements spaced repetition with mastery tracking:

- **Probability-based Question Selection**: Uses confidence scores to determine question difficulty
- **Mastery Buckets**: Tracks items as NOT_STARTED → IN_PROGRESS → MASTERED
- **Adaptive Review Scheduling**: Reviews mastered items with exponential backoff
- **Failed Item Retry**: Prioritizes items that were answered incorrectly

Based on analysis of:
- `assistantMode/learningModel/` - Core learning probability calculations
- `assistantMode/stepGenerators/` - Round generation and sequencing logic
- `assistantMode/enums/k.java` - Question type definitions

### 4. Session Management (`QuizletLearningSession`)
Orchestrates the complete learning experience:

- **Round Generation**: Creates learning rounds with optimal item selection
- **Progress Tracking**: Monitors overall learning progress and mastery
- **Retry Logic**: Ensures failed items are retried in subsequent rounds
- **Performance Analytics**: Provides detailed feedback and statistics

## Key Features Demonstrated

### Answer Sanitization
```python
# Handles various input variations
sanitizer.is_spelling_match("helo", "hello")  # True - spelling error
sanitizer.is_spelling_match("colour", "color")  # True - variant spelling  
sanitizer.sanitize_answer("  Hello, World!  ")  # "hello world"
```

### Adaptive Question Types
```python
# Low confidence → easier questions
vocab.probability_correct = 0.2
question_type = algorithm.select_question_type(vocab)  # MULTIPLE_CHOICE

# High confidence → harder questions  
vocab.probability_correct = 0.8
question_type = algorithm.select_question_type(vocab)  # WRITTEN
```

### Mastery Progression
```python
# Items progress through mastery levels
vocab.mastery_level  # NOT_STARTED → IN_PROGRESS → MASTERED
vocab.correct_streak  # Tracks consecutive correct answers
```

### Intelligent Round Generation
- Prioritizes failed items from previous rounds
- Balances new items with review items
- Considers mastery levels and review schedules
- Maintains optimal round sizes (default: 7 items like Quizlet)

## Usage

### Basic Learning Session
```python
from quizlet_learning_algorithm import VocabularyItem, QuizletLearningSession

# Create vocabulary
vocabulary = [
    VocabularyItem(1, "hello", "a greeting"),
    VocabularyItem(2, "goodbye", "a farewell"),
    # ... more items
]

# Start learning session
session = QuizletLearningSession(vocabulary, round_size=7)

# Generate round
round_items = session.start_new_round()

# Process each question
for vocab in round_items:
    question = session.generate_question(vocab)
    user_answer = input(f"What does '{vocab.term}' mean? ")
    
    result = session.submit_answer(vocab.id, user_answer, question['question_type'])
    
    if result['is_correct']:
        print("✅ Correct!")
    else:
        print(f"❌ Incorrect. Answer: {result['correct_answer']}")
```

### Running the Demo
```bash
# Full learning simulation with 20 vocabulary items
python3 quizlet_learning_algorithm.py

# Test suite demonstrating all features
python3 test_quizlet_algorithm.py
```

## Algorithm Details

### Probability Calculations
The algorithm uses probability-based decisions similar to Quizlet's approach:

```python
# Initial probability for new items
base_probability = 0.663
random_guess_probability = 0.25  # for multiple choice
question_difficulty_weight = 2.055  # for multiple choice

# Bayesian updates based on performance
if correct:
    probability *= 1.2  # Increase confidence
else:
    probability *= 0.8  # Decrease confidence
```

### Mastery Requirements
- **Mastery Threshold**: 2 consecutive correct answers (configurable)
- **Review Intervals**: Exponential backoff (2^n days) for mastered items
- **Retry Logic**: Failed items return to earlier mastery levels

### Round Generation Logic
1. Start with failed items from previous rounds
2. Add items that haven't reached mastery
3. Include some mastered items for review
4. Shuffle for variety
5. Maintain target round size

## Files

- `quizlet_learning_algorithm.py` - Main implementation with full algorithm
- `test_quizlet_algorithm.py` - Test suite demonstrating all features
- `README.md` - This documentation

## Key Insights from Quizlet App Analysis

The reimplementation is based on analysis of these key components from the decompiled app:

1. **Text Normalization** (`util/b.java`): Character mappings for international text
2. **Grading System** (`grading/`): Answer validation with spelling tolerance
3. **Question Types** (`assistantMode/enums/k.java`): 13 different question types
4. **Learning Model** (`assistantMode/learningModel/`): Probability-based difficulty selection
5. **Step Generation** (`assistantMode/stepGenerators/`): Round creation and sequencing
6. **Progress Tracking** (`com/quizlet/learn/data/`): Mastery buckets and statistics

The algorithm successfully captures Quizlet's core learning mechanics:
- **Adaptive Difficulty**: Questions get harder as confidence increases
- **Spaced Repetition**: Review intervals increase for mastered content
- **Error Recovery**: Failed items are prioritized for retry
- **Progress Tracking**: Clear progression through mastery levels

This implementation provides a functional reproduction of Quizlet's learning system that can be used for educational applications or further research into adaptive learning algorithms.