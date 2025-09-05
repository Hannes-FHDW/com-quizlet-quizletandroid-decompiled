#!/usr/bin/env python3
"""
Quizlet Learning Algorithm Reimplementation

This script reimplements the core Quizlet learning algorithm based on analysis 
of the decompiled Android app. It includes:

1. Text sanitization and answer validation
2. Question type selection (multiple choice vs written input)
3. Spaced repetition learning algorithm with mastery buckets
4. Progress tracking and retry logic for failed vocabulary

The algorithm uses probability-based decisions to determine question difficulty
and employs mastery buckets to track learning progress.
"""

import re
import random
import math
import json
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class QuestionType(Enum):
    """Question types based on assistantMode.enums.k from Quizlet app"""
    WRITTEN = 1
    MULTIPLE_CHOICE = 4
    TRUE_FALSE = 8
    FILL_IN_BLANK = 1024
    REVEAL_SELF_ASSESSMENT = 16


class QuestionDirection(Enum):
    """Direction of questions - which part to ask for"""
    TERM_TO_DEFINITION = "term_to_definition"  # Show term, ask for definition
    DEFINITION_TO_TERM = "definition_to_term"  # Show definition, ask for term
    MIXED = "mixed"  # Randomly choose direction


class MasteryLevel(Enum):
    """Learning progress levels for vocabulary items"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    MASTERED = "mastered"


@dataclass
class LearningConfiguration:
    """Configuration options for the learning session"""
    # Question type settings
    enabled_question_types: Set[QuestionType] = field(default_factory=lambda: {
        QuestionType.WRITTEN, 
        QuestionType.MULTIPLE_CHOICE, 
        QuestionType.TRUE_FALSE, 
        QuestionType.FILL_IN_BLANK
    })
    
    # Direction settings
    question_direction: QuestionDirection = QuestionDirection.TERM_TO_DEFINITION
    
    # Language-specific written question settings
    term_language_written_enabled: bool = True  # Enable written questions for term language
    definition_language_written_enabled: bool = True  # Enable written questions for definition language
    
    # Partial credit settings
    partial_credit_enabled: bool = True
    partial_credit_threshold: float = 0.7  # Minimum similarity for partial credit
    
    # Spelling tolerance
    spelling_tolerance: int = 2  # Maximum edit distance for spelling errors
    
    def is_question_type_enabled(self, question_type: QuestionType) -> bool:
        """Check if a question type is enabled"""
        return question_type in self.enabled_question_types
    
    def should_use_written_for_direction(self, direction: QuestionDirection) -> bool:
        """Check if written questions should be used for a specific direction"""
        if direction == QuestionDirection.TERM_TO_DEFINITION:
            return self.definition_language_written_enabled
        elif direction == QuestionDirection.DEFINITION_TO_TERM:
            return self.term_language_written_enabled
        else:
            # For mixed, use written if either direction allows it
            return self.term_language_written_enabled or self.definition_language_written_enabled


@dataclass
class VocabularyItem:
    """Represents a vocabulary word/phrase pair"""
    id: int
    term: str
    definition: str
    mastery_level: MasteryLevel = MasteryLevel.NOT_STARTED
    correct_streak: int = 0
    total_attempts: int = 0
    last_seen: Optional[datetime] = None
    probability_correct: float = 0.5  # Initial probability


@dataclass
class Answer:
    """User's answer to a question"""
    vocabulary_id: int
    user_input: str
    is_correct: bool
    question_type: QuestionType
    question_direction: QuestionDirection
    partial_score: float = 0.0  # Score between 0.0 and 1.0 for partial credit
    timestamp: datetime = field(default_factory=datetime.now)


class TextSanitizer:
    """
    Text sanitization based on grading/core and util/b.java from Quizlet app
    Handles character normalization, punctuation removal, and spelling tolerance
    """
    
    # Character normalization map from util.b.java
    CHARACTER_NORMALIZATIONS = {
        # Smart quotes and apostrophes
        '\u2019': "'", '\u2018': "'", '\u2032': "'", '\u00b4': "'",
        '\u201d': '"', '\u201c': '"', '\u2026': "...",
        # Whitespace characters  
        '\t': " ", '\u2002': " ", '\u0000': "",
        # Dashes and hyphens
        '\u2013': "-", '\u00ad': "",
        # Brackets and symbols
        '\u3031': "] ", '\u3030': " [", '\u00d7': "x",
        # Special characters
        '\u0219': "ş", '\u0153': "oe", '\u00e6': "ae", '\u00c6': "AE",
        # Cyrillic to Latin
        '\u0430': "a", '\u0410': "A", '\u0435': "e", '\u0415': "E",
        '\u0441': "c", '\u0421': "C", '\u0443': "y", '\u0423': "Y",
        # Japanese punctuation
        '\u3000': " ", '\u3001': ",", '\u3002': ".", '\u301c': "~",
        '\uff0c': ", ", '\uff0e': ". ", '\uff01': "! ", '\uff1f': "? ",
        '\uff1b': "; ", '\uff1a': ": ", '\uff08': " (", '\uff09': ") ",
        '\uff5e': "~ "
    }
    
    @classmethod
    def normalize_characters(cls, text: str) -> str:
        """Normalize similar characters to standard forms"""
        for char, replacement in cls.CHARACTER_NORMALIZATIONS.items():
            text = text.replace(char, replacement)
        return text
    
    @classmethod
    def remove_punctuation(cls, text: str) -> str:
        """Remove punctuation but preserve spaces"""
        # Keep alphanumeric and spaces, remove most punctuation
        return re.sub(r'[^\w\s]', '', text)
    
    @classmethod
    def sanitize_answer(cls, text: str) -> str:
        """
        Full sanitization pipeline:
        1. Normalize characters
        2. Trim whitespace
        3. Convert to lowercase
        4. Remove punctuation
        5. Normalize whitespace
        """
        if not text:
            return ""
            
        # Normalize characters
        text = cls.normalize_characters(text)
        
        # Basic cleanup
        text = text.strip().lower()
        
        # Remove punctuation
        text = cls.remove_punctuation(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @classmethod
    def levenshtein_distance(cls, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance for spell checking"""
        if len(s1) < len(s2):
            return cls.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def is_spelling_match(cls, user_answer: str, correct_answer: str, tolerance: float = 0.2) -> bool:
        """
        Check if answer is close enough considering spelling errors
        Based on grading/impls/levenshteinplus logic
        """
        user_clean = cls.sanitize_answer(user_answer)
        correct_clean = cls.sanitize_answer(correct_answer)
        
        if user_clean == correct_clean:
            return True
        
        # Calculate allowed errors based on length
        max_length = max(len(user_clean), len(correct_clean))
        if max_length == 0:
            return False
            
        max_errors = int(max_length * tolerance)
        distance = cls.levenshtein_distance(user_clean, correct_clean)
        
        return distance <= max_errors
    
    @classmethod
    def calculate_similarity_score(cls, user_answer: str, correct_answer: str) -> float:
        """
        Calculate similarity score between 0.0 and 1.0 for partial credit
        Returns 1.0 for exact match, decreasing based on edit distance
        """
        user_clean = cls.sanitize_answer(user_answer)
        correct_clean = cls.sanitize_answer(correct_answer)
        
        if user_clean == correct_clean:
            return 1.0
        
        if not user_clean or not correct_clean:
            return 0.0
        
        max_length = max(len(user_clean), len(correct_clean))
        distance = cls.levenshtein_distance(user_clean, correct_clean)
        
        # Calculate similarity as 1 - (distance / max_possible_distance)
        similarity = max(0.0, 1.0 - (distance / max_length))
        
        return similarity


class LearningAlgorithm:
    """
    Core learning algorithm based on assistantMode.learningModel from Quizlet app
    Implements probability-based question selection and mastery tracking
    """
    
    # Question type difficulty weights from learningModel.a
    QUESTION_TYPE_WEIGHTS = {
        QuestionType.MULTIPLE_CHOICE: 2.055,
        QuestionType.TRUE_FALSE: 1.962,
        QuestionType.WRITTEN: 1.0,
        QuestionType.FILL_IN_BLANK: 1.0,
        QuestionType.REVEAL_SELF_ASSESSMENT: 0.765
    }
    
    # Base probability for random guessing by question type
    RANDOM_GUESS_PROBABILITY = {
        QuestionType.MULTIPLE_CHOICE: 0.25,
        QuestionType.TRUE_FALSE: 0.5,
        QuestionType.WRITTEN: 0.0,
        QuestionType.FILL_IN_BLANK: 0.0,
        QuestionType.REVEAL_SELF_ASSESSMENT: 0.0
    }
    
    def __init__(self, mastery_threshold: int = 2, config: Optional[LearningConfiguration] = None):
        """
        Initialize learning algorithm
        
        Args:
            mastery_threshold: Number of consecutive correct answers needed for mastery
            config: Learning configuration options
        """
        self.mastery_threshold = mastery_threshold
        self.config = config or LearningConfiguration()
    
    def calculate_probability_correct(self, vocab: VocabularyItem, question_type: QuestionType) -> float:
        """
        Calculate probability of correct answer based on learning model
        Based on assistantMode.learningModel.a.d method
        """
        if vocab.total_attempts == 0:
            # Initial probability from base rates
            base_prob = 0.663  # Base probability for new items
            random_guess = self.RANDOM_GUESS_PROBABILITY.get(question_type, 0.0)
            weight = self.QUESTION_TYPE_WEIGHTS.get(question_type, 1.0)
            
            # Adjust for question difficulty
            adjusted_prob = base_prob * weight
            final_prob = adjusted_prob + (1 - adjusted_prob) * random_guess
            
            return min(1.0, max(0.0, final_prob))
        else:
            # Use historical performance
            return vocab.probability_correct
    
    def update_probability(self, vocab: VocabularyItem, is_correct: bool, question_type: QuestionType):
        """Update probability based on answer correctness"""
        # Simple Bayesian update
        if is_correct:
            vocab.probability_correct = min(1.0, vocab.probability_correct * 1.2)
        else:
            vocab.probability_correct = max(0.1, vocab.probability_correct * 0.8)
    
    def select_question_type(self, vocab: VocabularyItem, direction: QuestionDirection = QuestionDirection.TERM_TO_DEFINITION) -> QuestionType:
        """
        Select question type based on learner confidence and configuration
        Higher confidence -> harder question types
        """
        prob_correct = vocab.probability_correct
        
        # Get enabled question types
        enabled_types = list(self.config.enabled_question_types)
        if not enabled_types:
            # Fallback if no types enabled
            enabled_types = [QuestionType.MULTIPLE_CHOICE]
        
        # Filter written questions based on direction and configuration
        available_types = []
        for qtype in enabled_types:
            if qtype == QuestionType.WRITTEN:
                if self.config.should_use_written_for_direction(direction):
                    available_types.append(qtype)
            else:
                available_types.append(qtype)
        
        if not available_types:
            # Fallback if no types available after filtering
            available_types = [QuestionType.MULTIPLE_CHOICE]
        
        # Select based on confidence level, prioritizing enabled types
        if prob_correct < 0.3:
            # Low confidence: prefer easier types
            preferred = [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
            suitable = [t for t in preferred if t in available_types]
            if suitable:
                return random.choice(suitable)
        elif prob_correct < 0.6:
            # Medium confidence: mix of multiple choice and fill-in-blank
            preferred = [QuestionType.MULTIPLE_CHOICE, QuestionType.FILL_IN_BLANK, QuestionType.TRUE_FALSE]
            suitable = [t for t in preferred if t in available_types]
            if suitable:
                return random.choice(suitable)
        elif prob_correct < 0.8:
            # Higher confidence: written and fill-in-blank
            preferred = [QuestionType.WRITTEN, QuestionType.FILL_IN_BLANK]
            suitable = [t for t in preferred if t in available_types]
            if suitable:
                return random.choice(suitable)
        else:
            # High confidence: written answers preferred
            if QuestionType.WRITTEN in available_types:
                return QuestionType.WRITTEN
        
        # Fallback to any available type
        return random.choice(available_types)
    
    def update_mastery_level(self, vocab: VocabularyItem, is_correct: bool, partial_score: float = 1.0):
        """Update mastery level based on answer correctness and partial score"""
        if is_correct:
            vocab.correct_streak += 1
            if vocab.mastery_level == MasteryLevel.NOT_STARTED:
                vocab.mastery_level = MasteryLevel.IN_PROGRESS
            elif vocab.correct_streak >= self.mastery_threshold:
                vocab.mastery_level = MasteryLevel.MASTERED
        else:
            # For partial credit, reduce streak based on score
            if self.config.partial_credit_enabled and partial_score > 0:
                # Partial credit: reduce streak but don't reset to 0
                reduction = int((1.0 - partial_score) * vocab.correct_streak)
                vocab.correct_streak = max(0, vocab.correct_streak - reduction)
            else:
                # No partial credit: reset streak
                vocab.correct_streak = 0
            
            if vocab.mastery_level == MasteryLevel.MASTERED:
                vocab.mastery_level = MasteryLevel.IN_PROGRESS
    
    def should_review_item(self, vocab: VocabularyItem) -> bool:
        """
        Determine if item should be included in current round
        Based on spaced repetition principles
        """
        if vocab.mastery_level == MasteryLevel.NOT_STARTED:
            return True
        
        if vocab.mastery_level == MasteryLevel.MASTERED:
            # Review mastered items less frequently
            if vocab.last_seen is None:
                return True
            
            # Exponential backoff for review intervals
            days_since_last_seen = (datetime.now() - vocab.last_seen).days
            review_interval = 2 ** min(vocab.correct_streak, 5)  # Cap at 32 days
            
            return days_since_last_seen >= review_interval
        
        # Always review in-progress items
        return True


class QuizletLearningSession:
    """
    Main learning session that orchestrates the learning process
    Based on assistantMode.stepGenerators.a from Quizlet app
    """
    
    def __init__(self, vocabulary_list: List[VocabularyItem], round_size: int = 7, config: Optional[LearningConfiguration] = None):
        """
        Initialize learning session
        
        Args:
            vocabulary_list: List of vocabulary items to learn
            round_size: Number of items per round (based on Quizlet's default)
            config: Learning configuration options
        """
        self.vocabulary = {item.id: item for item in vocabulary_list}
        self.round_size = round_size
        self.config = config or LearningConfiguration()
        self.learning_algorithm = LearningAlgorithm(config=self.config)
        self.text_sanitizer = TextSanitizer()
        
        # Session state
        self.current_round: List[VocabularyItem] = []
        self.round_answers: List[Answer] = []
        self.session_answers: List[Answer] = []
        self.failed_items: Set[int] = set()
    
    def start_new_round(self) -> List[VocabularyItem]:
        """
        Start a new learning round
        Selects items based on mastery level and review scheduling
        """
        # Get items that need review
        items_to_review = [
            vocab for vocab in self.vocabulary.values()
            if self.learning_algorithm.should_review_item(vocab)
        ]
        
        # Prioritize failed items from previous rounds
        failed_items = [
            self.vocabulary[item_id] for item_id in self.failed_items
            if item_id in self.vocabulary
        ]
        
        # Start with failed items, then add new items
        round_items = failed_items.copy()
        
        # Add items that haven't been mastered
        remaining_slots = self.round_size - len(round_items)
        if remaining_slots > 0:
            not_mastered = [
                item for item in items_to_review
                if item.mastery_level != MasteryLevel.MASTERED
                and item.id not in self.failed_items
            ]
            round_items.extend(not_mastered[:remaining_slots])
        
        # If still have slots, add some mastered items for review
        remaining_slots = self.round_size - len(round_items)
        if remaining_slots > 0:
            mastered_review = [
                item for item in items_to_review
                if item.mastery_level == MasteryLevel.MASTERED
                and item.id not in self.failed_items
            ]
            round_items.extend(mastered_review[:remaining_slots])
        
        # Shuffle the round
        random.shuffle(round_items)
        
        self.current_round = round_items
        self.round_answers = []
        self.failed_items.clear()
        
        return round_items
    
    def generate_question(self, vocab: VocabularyItem) -> Dict:
        """Generate a question for the given vocabulary item"""
        # Determine question direction
        direction = self._select_question_direction()
        
        # Select question type based on direction and configuration
        question_type = self.learning_algorithm.select_question_type(vocab, direction)
        
        question = {
            'vocabulary_id': vocab.id,
            'term': vocab.term,
            'definition': vocab.definition,
            'question_type': question_type,
            'question_direction': direction,
            'probability_correct': vocab.probability_correct
        }
        
        # Set the prompt and correct answer based on direction
        if direction == QuestionDirection.TERM_TO_DEFINITION:
            question['prompt'] = vocab.term
            question['correct_answer'] = vocab.definition
        elif direction == QuestionDirection.DEFINITION_TO_TERM:
            question['prompt'] = vocab.definition
            question['correct_answer'] = vocab.term
        else:
            # Mixed direction - randomly choose
            if random.choice([True, False]):
                question['prompt'] = vocab.term
                question['correct_answer'] = vocab.definition
                question['actual_direction'] = QuestionDirection.TERM_TO_DEFINITION
            else:
                question['prompt'] = vocab.definition
                question['correct_answer'] = vocab.term
                question['actual_direction'] = QuestionDirection.DEFINITION_TO_TERM
        
        if question_type == QuestionType.MULTIPLE_CHOICE:
            # Generate distractors for multiple choice
            question['options'] = self._generate_multiple_choice_options(vocab, direction)
        
        return question
    
    def _select_question_direction(self) -> QuestionDirection:
        """Select question direction based on configuration"""
        if self.config.question_direction == QuestionDirection.MIXED:
            # Randomly choose direction for mixed mode
            return random.choice([QuestionDirection.TERM_TO_DEFINITION, QuestionDirection.DEFINITION_TO_TERM])
        else:
            return self.config.question_direction
    
    def _generate_multiple_choice_options(self, vocab: VocabularyItem, direction: QuestionDirection) -> List[str]:
        """Generate multiple choice options with distractors based on direction"""
        if direction == QuestionDirection.TERM_TO_DEFINITION:
            correct_answer = vocab.definition
            # Get other definitions as distractors
            other_options = [
                v.definition for v in self.vocabulary.values()
                if v.id != vocab.id and v.definition != vocab.definition
            ]
        else:  # DEFINITION_TO_TERM
            correct_answer = vocab.term
            # Get other terms as distractors
            other_options = [
                v.term for v in self.vocabulary.values()
                if v.id != vocab.id and v.term != vocab.term
            ]
        
        options = [correct_answer]
        
        # Add 3 random distractors
        distractors = random.sample(other_options, min(3, len(other_options)))
        options.extend(distractors)
        
        # Shuffle options
        random.shuffle(options)
        
        return options
    
    def submit_answer(self, vocabulary_id: int, user_input: str, question_type: QuestionType, 
                      question_direction: QuestionDirection, correct_answer: str) -> Dict:
        """
        Submit an answer and get feedback
        Returns result with correctness and partial credit
        """
        vocab = self.vocabulary[vocabulary_id]
        
        # Initialize scores
        is_correct = False
        partial_score = 0.0
        
        # Determine correctness based on question type
        if question_type == QuestionType.MULTIPLE_CHOICE:
            is_correct = user_input.strip() == correct_answer
            partial_score = 1.0 if is_correct else 0.0
        else:
            # For written answers, use text sanitization and spell checking
            if self.config.partial_credit_enabled:
                # Calculate similarity score for partial credit
                partial_score = self.text_sanitizer.calculate_similarity_score(user_input, correct_answer)
                is_correct = partial_score >= self.config.partial_credit_threshold
            else:
                # Binary scoring
                is_correct = self.text_sanitizer.is_spelling_match(
                    user_input, correct_answer, 
                    tolerance=self.config.spelling_tolerance / max(len(correct_answer), 1)
                )
                partial_score = 1.0 if is_correct else 0.0
        
        # Create answer record
        answer = Answer(
            vocabulary_id=vocabulary_id,
            user_input=user_input,
            is_correct=is_correct,
            question_type=question_type,
            question_direction=question_direction,
            partial_score=partial_score
        )
        
        # Update vocabulary statistics
        vocab.total_attempts += 1
        vocab.last_seen = datetime.now()
        
        # Update learning algorithm
        self.learning_algorithm.update_probability(vocab, is_correct, question_type)
        self.learning_algorithm.update_mastery_level(vocab, is_correct, partial_score)
        
        # Track failed items for retry (considering partial credit)
        if not is_correct or (self.config.partial_credit_enabled and partial_score < self.config.partial_credit_threshold):
            self.failed_items.add(vocabulary_id)
        
        # Store answer
        self.round_answers.append(answer)
        self.session_answers.append(answer)
        
        result = {
            'is_correct': is_correct,
            'partial_score': partial_score,
            'correct_answer': correct_answer,
            'user_answer': user_input,
            'sanitized_user_answer': self.text_sanitizer.sanitize_answer(user_input),
            'sanitized_correct_answer': self.text_sanitizer.sanitize_answer(correct_answer),
            'mastery_level': vocab.mastery_level.value,
            'correct_streak': vocab.correct_streak,
            'probability_correct': vocab.probability_correct,
            'question_direction': question_direction.value
        }
        
        return result
    
    def get_round_summary(self) -> Dict:
        """Get summary of current round performance"""
        if not self.round_answers:
            return {'total': 0, 'correct': 0, 'percentage': 0.0}
        
        total = len(self.round_answers)
        correct = sum(1 for answer in self.round_answers if answer.is_correct)
        percentage = (correct / total) * 100
        
        return {
            'total': total,
            'correct': correct,
            'percentage': percentage,
            'failed_items': list(self.failed_items)
        }
    
    def get_overall_progress(self) -> Dict:
        """Get overall learning progress"""
        total_items = len(self.vocabulary)
        mastery_counts = {level: 0 for level in MasteryLevel}
        
        for vocab in self.vocabulary.values():
            mastery_counts[vocab.mastery_level] += 1
        
        mastered_percentage = (mastery_counts[MasteryLevel.MASTERED] / total_items) * 100
        
        return {
            'total_items': total_items,
            'not_started': mastery_counts[MasteryLevel.NOT_STARTED],
            'in_progress': mastery_counts[MasteryLevel.IN_PROGRESS],
            'mastered': mastery_counts[MasteryLevel.MASTERED],
            'mastered_percentage': mastered_percentage,
            'total_answers': len(self.session_answers)
        }
    
    def is_round_complete(self) -> bool:
        """Check if current round is complete"""
        return len(self.round_answers) >= len(self.current_round)
    
    def should_continue_session(self) -> bool:
        """Determine if learning session should continue"""
        # Continue if there are items that need more practice
        items_needing_practice = [
            vocab for vocab in self.vocabulary.values()
            if vocab.mastery_level != MasteryLevel.MASTERED or self.failed_items
        ]
        
        return len(items_needing_practice) > 0


def create_sample_vocabulary() -> List[VocabularyItem]:
    """Create sample vocabulary for testing"""
    sample_vocab = [
        ("hello", "a greeting"),
        ("goodbye", "a farewell"),
        ("thank you", "an expression of gratitude"),
        ("please", "a polite request word"),
        ("sorry", "an apology"),
        ("house", "a building where people live"),
        ("car", "a motor vehicle"),
        ("book", "written or printed work"),
        ("water", "clear liquid essential for life"),
        ("food", "substances consumed for nutrition"),
        ("happy", "feeling joy or pleasure"),
        ("sad", "feeling sorrow or unhappiness"),
        ("big", "large in size"),
        ("small", "little in size"),
        ("red", "color of blood"),
        ("blue", "color of sky"),
        ("green", "color of grass"),
        ("black", "darkest color"),
        ("white", "lightest color"),
        ("yellow", "color of sun")
    ]
    
    vocabulary_list = []
    for i, (term, definition) in enumerate(sample_vocab):
        vocabulary_list.append(VocabularyItem(
            id=i + 1,
            term=term,
            definition=definition
        ))
    
    return vocabulary_list


def main():
    """Main function to demonstrate the learning algorithm"""
    print("🎓 Quizlet Learning Algorithm Reimplementation")
    print("=" * 50)
    
    # Demo different configurations
    configs = [
        ("Standard Configuration", LearningConfiguration()),
        ("German-English Mixed", LearningConfiguration(
            question_direction=QuestionDirection.MIXED,
            partial_credit_enabled=True
        )),
        ("Multiple Choice Only", LearningConfiguration(
            enabled_question_types={QuestionType.MULTIPLE_CHOICE}
        )),
        ("Written Only with Partial Credit", LearningConfiguration(
            enabled_question_types={QuestionType.WRITTEN},
            partial_credit_enabled=True,
            partial_credit_threshold=0.6
        ))
    ]
    
    for config_name, config in configs:
        print(f"\n🔧 {config_name}")
        print("=" * 50)
        
        # Create sample vocabulary for German-English
        vocabulary = [
            VocabularyItem(1, "hello", "hallo"),
            VocabularyItem(2, "goodbye", "auf wiedersehen"),
            VocabularyItem(3, "thank you", "danke"),
            VocabularyItem(4, "please", "bitte"),
            VocabularyItem(5, "house", "haus")
        ]
        
        # Initialize learning session with configuration
        session = QuizletLearningSession(vocabulary, round_size=3, config=config)
        
        print(f"\n📚 Loaded {len(vocabulary)} vocabulary items")
        print(f"Question direction: {config.question_direction.value}")
        print(f"Enabled question types: {[qt.name for qt in config.enabled_question_types]}")
        print(f"Partial credit: {'Enabled' if config.partial_credit_enabled else 'Disabled'}")
        
        # Simulate one round
        round_items = session.start_new_round()
        print(f"\n🔄 Learning {len(round_items)} items")
        print("-" * 30)
        
        # Process each item in the round
        for vocab in round_items:
            question = session.generate_question(vocab)
            
            print(f"\n📝 Prompt: {question['prompt']}")
            print(f"Question type: {question['question_type'].name}")
            print(f"Direction: {question['question_direction'].value}")
            
            if question['question_type'] == QuestionType.MULTIPLE_CHOICE:
                print("Options:")
                for i, option in enumerate(question['options'], 1):
                    print(f"  {i}. {option}")
                
                # Simulate user selection (choose correct answer 80% of the time)
                if random.random() < 0.8:
                    user_answer = question['correct_answer']
                else:
                    user_answer = random.choice([opt for opt in question['options'] if opt != question['correct_answer']])
                print(f"Selected: {user_answer}")
            else:
                # Simulate written answer with various accuracy levels
                correct_answer = question['correct_answer']
                accuracy_roll = random.random()
                
                if accuracy_roll < 0.6:  # 60% perfect answer
                    user_answer = correct_answer
                elif accuracy_roll < 0.8:  # 20% spelling error
                    # Introduce a small spelling error
                    if len(correct_answer) > 3:
                        pos = random.randint(1, len(correct_answer) - 2)
                        user_answer = correct_answer[:pos] + correct_answer[pos+1:]  # Remove one character
                    else:
                        user_answer = correct_answer + "x"  # Add extra character
                else:  # 20% wrong answer
                    user_answer = "completely wrong"
                
                print(f"Answer: {user_answer}")
            
            # Submit answer with new signature
            result = session.submit_answer(
                vocab.id, 
                user_answer, 
                question['question_type'],
                question['question_direction'],
                question['correct_answer']
            )
            
            # Show feedback
            if result['is_correct']:
                print("✅ Correct!")
            else:
                print("❌ Incorrect")
                print(f"Correct answer: {result['correct_answer']}")
            
            if config.partial_credit_enabled:
                print(f"Partial score: {result['partial_score']:.2f}")
            
            print(f"Mastery: {result['mastery_level']} (streak: {result['correct_streak']})")
        
        # Round summary
        summary = session.get_round_summary()
        print(f"\n📊 Summary:")
        print(f"Correct: {summary['correct']}/{summary['total']} ({summary['percentage']:.1f}%)")
        
        if summary['failed_items']:
            print(f"Failed items for retry: {summary['failed_items']}")
        
        print("\n" + "=" * 50)


if __name__ == "__main__":
    main()