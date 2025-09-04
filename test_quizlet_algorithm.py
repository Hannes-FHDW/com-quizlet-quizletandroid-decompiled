#!/usr/bin/env python3
"""
Test and demonstration script for the Quizlet Learning Algorithm reimplementation.

This script demonstrates the key features:
1. Text sanitization and spell checking
2. Question type selection based on confidence
3. Learning algorithm behavior
4. Progress tracking
"""

from quizlet_learning_algorithm import (
    TextSanitizer, VocabularyItem, QuizletLearningSession, 
    QuestionType, MasteryLevel, LearningAlgorithm
)
import random


def test_text_sanitization():
    """Test the text sanitization features"""
    print("🧹 Testing Text Sanitization")
    print("=" * 40)
    
    # Test cases from Quizlet's normalization
    test_cases = [
        ("Hello's", "hello's"),  # Smart quotes
        ("café", "cafe"),        # Accents (if implemented)
        ("  Hello  World  ", "hello world"),  # Whitespace
        ("Hello, World!", "hello world"),     # Punctuation
        ("HELLO", "hello"),      # Case
        ("color", "colour"),     # Spelling variations
    ]
    
    sanitizer = TextSanitizer()
    
    for original, expected_clean in test_cases:
        cleaned = sanitizer.sanitize_answer(original)
        print(f"'{original}' -> '{cleaned}'")
    
    print("\n🔍 Testing Spell Checking")
    print("-" * 25)
    
    # Test spell checking with different tolerances
    spell_tests = [
        ("hello", "helo", True),      # Missing letter
        ("hello", "hallo", True),     # Substitution  
        ("hello", "helllo", True),    # Extra letter
        ("hello", "goodbye", False),  # Completely different
        ("color", "colour", True),    # British/American spelling
        ("definitely", "definately", True),  # Common misspelling
    ]
    
    for correct, user_input, expected_match in spell_tests:
        is_match = sanitizer.is_spelling_match(user_input, correct)
        status = "✅" if is_match == expected_match else "❌"
        print(f"{status} '{user_input}' vs '{correct}': {is_match}")


def test_question_type_selection():
    """Test how question types are selected based on confidence"""
    print("\n🎯 Testing Question Type Selection")
    print("=" * 40)
    
    algorithm = LearningAlgorithm()
    
    # Create vocabulary items with different confidence levels
    confidence_levels = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    for confidence in confidence_levels:
        vocab = VocabularyItem(1, "test", "test definition")
        vocab.probability_correct = confidence
        
        question_type = algorithm.select_question_type(vocab)
        print(f"Confidence {confidence:.1f} -> {question_type.name}")


def test_learning_progression():
    """Test the learning progression through mastery levels"""
    print("\n📈 Testing Learning Progression")
    print("=" * 40)
    
    vocab = VocabularyItem(1, "hello", "a greeting")
    algorithm = LearningAlgorithm(mastery_threshold=2)
    
    print(f"Initial state: {vocab.mastery_level.value}, streak: {vocab.correct_streak}")
    
    # Simulate a series of answers
    answers = [True, True, False, True, True]  # Correct, Correct, Wrong, Correct, Correct
    
    for i, is_correct in enumerate(answers):
        algorithm.update_mastery_level(vocab, is_correct)
        algorithm.update_probability(vocab, is_correct, QuestionType.WRITTEN)
        
        print(f"Answer {i+1} ({'Correct' if is_correct else 'Wrong'}): "
              f"{vocab.mastery_level.value}, streak: {vocab.correct_streak}, "
              f"confidence: {vocab.probability_correct:.2f}")


def test_round_generation():
    """Test how learning rounds are generated"""
    print("\n🔄 Testing Round Generation")
    print("=" * 40)
    
    # Create vocabulary with different mastery levels
    vocabulary = [
        VocabularyItem(1, "new1", "definition1"),  # Not started
        VocabularyItem(2, "new2", "definition2"),  # Not started
        VocabularyItem(3, "progress1", "definition3"),  # In progress
        VocabularyItem(4, "progress2", "definition4"),  # In progress  
        VocabularyItem(5, "mastered1", "definition5"),  # Mastered
    ]
    
    # Set up different mastery levels
    vocabulary[2].mastery_level = MasteryLevel.IN_PROGRESS
    vocabulary[2].correct_streak = 1
    vocabulary[3].mastery_level = MasteryLevel.IN_PROGRESS  
    vocabulary[3].correct_streak = 1
    vocabulary[4].mastery_level = MasteryLevel.MASTERED
    vocabulary[4].correct_streak = 2
    
    session = QuizletLearningSession(vocabulary, round_size=3)
    
    # Generate a round
    round_items = session.start_new_round()
    
    print(f"Generated round with {len(round_items)} items:")
    for item in round_items:
        print(f"  {item.term} ({item.mastery_level.value})")
    
    print(f"\nPriority order (should favor not started and in progress):")
    for item in round_items:
        priority = 3 if item.mastery_level == MasteryLevel.NOT_STARTED else \
                  2 if item.mastery_level == MasteryLevel.IN_PROGRESS else 1
        print(f"  {item.term}: priority {priority}")


def demonstrate_full_learning_cycle():
    """Demonstrate a complete learning cycle with detailed output"""
    print("\n🎓 Full Learning Cycle Demonstration")  
    print("=" * 50)
    
    # Create small vocabulary set
    vocabulary = [
        VocabularyItem(1, "hello", "a greeting"),
        VocabularyItem(2, "goodbye", "a farewell"),
        VocabularyItem(3, "please", "a polite request"),
    ]
    
    session = QuizletLearningSession(vocabulary, round_size=2)
    
    print("Starting vocabulary:")
    for vocab in vocabulary:
        print(f"  {vocab.term} -> {vocab.definition}")
    
    # Simulate one complete round
    round_items = session.start_new_round()
    
    print(f"\n📝 Round 1: Learning {len(round_items)} items")
    
    for vocab in round_items:
        question = session.generate_question(vocab)
        print(f"\nQuestion: {vocab.term}")
        print(f"Type: {question['question_type'].name}")
        print(f"Confidence: {question['probability_correct']:.2f}")
        
        if question['question_type'] == QuestionType.MULTIPLE_CHOICE:
            print("Options:")
            for i, option in enumerate(question['options'], 1):
                print(f"  {i}. {option}")
            
            # Simulate correct answer
            user_answer = vocab.definition
        else:
            # Simulate written answer with occasional errors
            if random.random() < 0.8:  # 80% chance correct
                user_answer = vocab.definition
            else:
                user_answer = vocab.definition[:-1]  # Remove last character
        
        print(f"User answer: '{user_answer}'")
        
        result = session.submit_answer(vocab.id, user_answer, question['question_type'])
        
        print(f"Result: {'✅ Correct' if result['is_correct'] else '❌ Incorrect'}")
        print(f"Mastery: {result['mastery_level']} (streak: {result['correct_streak']})")
        
        if not result['is_correct']:
            print(f"Correct answer was: '{result['correct_answer']}'")
    
    # Show round summary
    summary = session.get_round_summary()
    print(f"\n📊 Round Summary:")
    print(f"Score: {summary['correct']}/{summary['total']} ({summary['percentage']:.1f}%)")
    
    if summary['failed_items']:
        print(f"Items to retry: {summary['failed_items']}")
    
    # Show overall progress
    progress = session.get_overall_progress()
    print(f"\n🎯 Overall Progress:")
    print(f"Mastered: {progress['mastered']}/{progress['total_items']} "
          f"({progress['mastered_percentage']:.1f}%)")


def main():
    """Run all test demonstrations"""
    print("🧪 Quizlet Learning Algorithm - Test Suite")
    print("=" * 50)
    
    # Run all tests
    test_text_sanitization()
    test_question_type_selection()
    test_learning_progression()
    test_round_generation()
    demonstrate_full_learning_cycle()
    
    print("\n✅ All tests completed!")
    print("\nKey Features Demonstrated:")
    print("- Text sanitization and spell checking tolerance")
    print("- Adaptive question type selection based on confidence")
    print("- Mastery level progression through correct/incorrect answers")  
    print("- Intelligent round generation prioritizing struggling items")
    print("- Complete learning cycle with progress tracking")


if __name__ == "__main__":
    main()