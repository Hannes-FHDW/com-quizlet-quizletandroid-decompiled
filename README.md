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
    
    result = session.submit_answer(
        vocab.id, 
        user_answer, 
        question['question_type'],
        question['question_direction'],
        question['correct_answer']
    )
    
    if result['is_correct']:
        print("✅ Correct!")
    else:
        print(f"❌ Incorrect. Answer: {result['correct_answer']}")
```

### Advanced Configuration Features

The learning system supports extensive configuration options for different learning scenarios:

#### Question Direction Control
```python
from quizlet_learning_algorithm import LearningConfiguration, QuestionDirection

# Ask for English given German
config = LearningConfiguration(
    question_direction=QuestionDirection.DEFINITION_TO_TERM
)

# Mixed: randomly ask for either direction  
config = LearningConfiguration(
    question_direction=QuestionDirection.MIXED
)

# Traditional: ask for definition given term (default)
config = LearningConfiguration(
    question_direction=QuestionDirection.TERM_TO_DEFINITION
)
```

#### Question Type Filtering
```python
# Only multiple choice questions
config = LearningConfiguration(
    enabled_question_types={QuestionType.MULTIPLE_CHOICE}
)

# Only written questions (hardest mode)
config = LearningConfiguration(
    enabled_question_types={QuestionType.WRITTEN}
)

# Disable written questions entirely
config = LearningConfiguration(
    enabled_question_types={
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TRUE_FALSE,
        QuestionType.FILL_IN_BLANK
    }
)
```

#### Language-Specific Written Questions
```python
# Disable written questions when asking for English
config = LearningConfiguration(
    term_language_written_enabled=False,    # No written for English
    definition_language_written_enabled=True  # Allow written for German
)

# Disable written questions when asking for German  
config = LearningConfiguration(
    term_language_written_enabled=True,     # Allow written for English
    definition_language_written_enabled=False  # No written for German
)
```

#### Partial Credit System
```python
# Enable partial credit with 70% threshold
config = LearningConfiguration(
    partial_credit_enabled=True,
    partial_credit_threshold=0.7,  # Need 70% similarity to be "correct"
    spelling_tolerance=2  # Allow up to 2 character differences
)

# Example: "helo" vs "hello" gets 80% similarity score
result = session.submit_answer(vocab.id, "helo", ...)
print(f"Similarity: {result['partial_score']}")  # 0.8
print(f"Correct: {result['is_correct']}")        # True (>= 0.7 threshold)
```

#### Complete Configuration Example
```python
# German-English learning with flexible settings
config = LearningConfiguration(
    question_direction=QuestionDirection.MIXED,
    enabled_question_types={
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.WRITTEN,
        QuestionType.FILL_IN_BLANK
    },
    term_language_written_enabled=True,     # Allow written for English
    definition_language_written_enabled=False,  # No written for German
    partial_credit_enabled=True,
    partial_credit_threshold=0.6,
    spelling_tolerance=2
)

session = QuizletLearningSession(vocabulary, config=config)
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

## New Features (Latest Update)

### Multiple Correct Answers
The system now supports vocabulary items with multiple possible correct answers separated by `/`, `,`, or `;`:

```python
# Example vocabulary with multiple answers
vocabulary = [
    VocabularyItem(1, "color", "color/colour"),  # American/British spelling
    VocabularyItem(2, "hello", "hi/hey/greeting"),  # Multiple synonyms
    VocabularyItem(3, "car", "automobile/vehicle")  # Alternative terms
]

# All of these answers would be accepted as correct:
# User types "color" or "colour" -> both correct
# User types "hi", "hey", or "greeting" -> all correct
```

### Quizlet API Integration
Load vocabulary sets directly from Quizlet using their public API:

```python
from quizlet_learning_algorithm import QuizletAPI

# Load from Quizlet URL
url = "https://quizlet.com/de/karteikarten/hi-403022052"
vocabulary = QuizletAPI.fetch_from_url(url)

# Or extract set ID and fetch directly
set_id = QuizletAPI.extract_set_id(url)
vocabulary = QuizletAPI.fetch_vocabulary_set(set_id)

# Use with learning session
session = QuizletLearningSession(vocabulary, config=config)
```

### Enhanced Answer Validation
The answer validation system now:
- Checks user input against all possible correct answers
- Returns the highest similarity score among all possible answers
- Supports partial credit for any valid answer variation
- Maintains backward compatibility with single-answer vocabulary

### Usage Example
```python
# Interactive vocabulary loading with Quizlet integration
vocabulary = load_vocabulary_from_quizlet()  # Prompts for Quizlet URL

# Create session with multiple answer support
session = QuizletLearningSession(vocabulary, config=LearningConfiguration(
    partial_credit_enabled=True,
    partial_credit_threshold=0.7
))

# The system automatically handles multiple answers in validation
```