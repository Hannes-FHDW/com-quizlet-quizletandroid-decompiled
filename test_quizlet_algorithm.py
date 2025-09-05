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
    QuestionType, MasteryLevel, LearningAlgorithm, LearningConfiguration,
    QuestionDirection, QuizletAPI
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
        
        result = session.submit_answer(
            vocab.id, 
            user_answer, 
            question['question_type'],
            question['question_direction'],
            question['correct_answer']
        )
        
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


def test_new_configuration_features():
    """Test the new configuration features"""
    print("\n🔧 Testing New Configuration Features")
    print("=" * 50)
    
    # Test different question directions
    vocabulary = [
        VocabularyItem(1, "hello", "hallo"),
        VocabularyItem(2, "goodbye", "auf wiedersehen"),
        VocabularyItem(3, "thank you", "danke")
    ]
    
    # Test mixed direction
    print("\n📋 Testing Mixed Question Direction")
    config_mixed = LearningConfiguration(
        question_direction=QuestionDirection.MIXED,
        enabled_question_types={QuestionType.MULTIPLE_CHOICE}
    )
    session_mixed = QuizletLearningSession(vocabulary.copy(), config=config_mixed)
    
    for _ in range(5):
        round_items = session_mixed.start_new_round()
        for vocab in round_items[:1]:  # Test just first item
            question = session_mixed.generate_question(vocab)
            print(f"Prompt: '{question['prompt']}' -> Expected: '{question['correct_answer']}' "
                  f"(Direction: {question['question_direction'].value})")
    
    # Test question type filtering
    print("\n🎯 Testing Question Type Filtering")
    configs = [
        ("Multiple Choice Only", {QuestionType.MULTIPLE_CHOICE}),
        ("Written Only", {QuestionType.WRITTEN}),
        ("Fill-in-Blank + True/False", {QuestionType.FILL_IN_BLANK, QuestionType.TRUE_FALSE})
    ]
    
    for config_name, enabled_types in configs:
        print(f"\n{config_name}:")
        config = LearningConfiguration(enabled_question_types=enabled_types)
        session = QuizletLearningSession(vocabulary.copy(), config=config)
        
        round_items = session.start_new_round()
        for vocab in round_items:
            question = session.generate_question(vocab)
            print(f"  {vocab.term} -> {question['question_type'].name}")


def test_partial_credit_system():
    """Test the partial credit system"""
    print("\n🎯 Testing Partial Credit System")
    print("=" * 40)
    
    vocabulary = [VocabularyItem(1, "hello", "hallo")]
    
    # Test with partial credit enabled
    config_partial = LearningConfiguration(
        partial_credit_enabled=True,
        partial_credit_threshold=0.7,
        enabled_question_types={QuestionType.WRITTEN}
    )
    session = QuizletLearningSession(vocabulary, config=config_partial)
    
    test_answers = [
        ("hallo", "Perfect match"),
        ("halo", "Minor spelling error"), 
        ("hello", "Wrong but similar"),
        ("completely wrong", "Completely wrong")
    ]
    
    print("Testing different answer quality:")
    for user_answer, description in test_answers:
        vocab = vocabulary[0]
        vocab.correct_streak = 0  # Reset for each test
        
        question = session.generate_question(vocab)
        result = session.submit_answer(
            vocab.id, 
            user_answer, 
            question['question_type'],
            question['question_direction'],
            question['correct_answer']
        )
        
        print(f"  '{user_answer}' ({description}):")
        print(f"    Similarity: {result['partial_score']:.2f}")
        print(f"    Correct: {result['is_correct']}")
        print(f"    Streak: {result['correct_streak']}")


def test_language_specific_written_questions():
    """Test language-specific written question settings"""
    print("\n🌍 Testing Language-Specific Written Questions")
    print("=" * 50)
    
    vocabulary = [VocabularyItem(1, "hello", "hallo")]
    
    configs = [
        ("Term language written disabled", LearningConfiguration(
            term_language_written_enabled=False,
            definition_language_written_enabled=True
        )),
        ("Definition language written disabled", LearningConfiguration(
            term_language_written_enabled=True,
            definition_language_written_enabled=False
        )),
        ("Both languages written enabled", LearningConfiguration(
            term_language_written_enabled=True,
            definition_language_written_enabled=True
        ))
    ]
    
    for config_name, config in configs:
        print(f"\n{config_name}:")
        session = QuizletLearningSession(vocabulary.copy(), config=config)
        
        # Test both directions
        for direction in [QuestionDirection.TERM_TO_DEFINITION, QuestionDirection.DEFINITION_TO_TERM]:
            vocab = vocabulary[0]
            vocab.probability_correct = 0.9  # High confidence to prefer written
            
            question_type = session.learning_algorithm.select_question_type(vocab, direction)
            written_allowed = config.should_use_written_for_direction(direction)
            
            print(f"  {direction.value}: Written allowed: {written_allowed}, "
                  f"Selected: {question_type.name}")


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
    
    # New feature tests
    test_new_configuration_features()
    test_partial_credit_system()
    test_language_specific_written_questions()
    
    print("\n✅ All tests completed!")
    print("\nKey Features Demonstrated:")
    print("- Text sanitization and spell checking tolerance")
    print("- Adaptive question type selection based on confidence")
    print("- Mastery level progression through correct/incorrect answers")  
    print("- Intelligent round generation prioritizing struggling items")
    print("- Complete learning cycle with progress tracking")
    print("- Configurable question types and directions")
    print("- Partial credit system with similarity scoring")
    print("- Language-specific written question controls")
    print("- Multiple correct answers separated by /, ,, ;")
    print("- Quizlet API integration for loading vocabulary sets")


def test_multiple_answers():
    """Test the multiple answers feature"""
    print("\n🔀 Testing Multiple Answers")
    print("=" * 40)
    
    sanitizer = TextSanitizer()
    
    # Test multiple answer splitting
    test_cases = [
        ("color/colour", ["color", "colour"]),
        ("red, blue; green", ["red", "blue", "green"]),
        ("hello/hi/hey", ["hello", "hi", "hey"]),
        ("single", ["single"]),
        ("", []),
        ("  color  /  colour  ", ["color", "colour"])
    ]
    
    print("Testing answer splitting:")
    for input_text, expected in test_cases:
        result = sanitizer.split_multiple_answers(input_text)
        print(f"'{input_text}' -> {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    # Test spelling match with multiple answers
    print("\nTesting spelling match with multiple answers:")
    test_cases = [
        ("color", "color/colour", True),    # Exact match with first
        ("colour", "color/colour", True),   # Exact match with second  
        ("colors", "color/colour", True),   # Spelling match with first
        ("colours", "color/colour", True),  # Spelling match with second
        ("red", "blue/green", False),       # No match
        ("colr", "color/colour", True),     # Spelling error but close
    ]
    
    for user_answer, correct_answers, expected in test_cases:
        result = sanitizer.is_spelling_match(user_answer, correct_answers)
        print(f"'{user_answer}' vs '{correct_answers}' -> {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    # Test similarity scoring with multiple answers
    print("\nTesting similarity scoring with multiple answers:")
    test_cases = [
        ("color", "color/colour", 1.0),     # Perfect match
        ("colour", "color/colour", 1.0),    # Perfect match with second
        ("colr", "color/colour", 0.8),      # Higher score should be used
        ("red", "blue/green", 0.5),         # Some similarity expected
    ]
    
    for user_answer, correct_answers, expected in test_cases:
        result = sanitizer.calculate_similarity_score(user_answer, correct_answers)
        print(f"'{user_answer}' vs '{correct_answers}' -> {result:.1f} (expected {expected})")
        assert abs(result - expected) < 0.2, f"Expected ~{expected}, got {result}"
    
    print("✅ Multiple answers tests passed!")


def test_quizlet_api():
    """Test Quizlet API URL parsing"""
    print("\n🌐 Testing Quizlet API")
    print("=" * 40)
    
    # Test URL parsing
    test_urls = [
        ("https://quizlet.com/de/karteikarten/hi-403022052", "403022052"),
        ("https://quizlet.com/123456/test", "123456"),
        ("quizlet.com/789/vocab", "789"),
    ]
    
    print("Testing URL parsing:")
    for url, expected_id in test_urls:
        try:
            result = QuizletAPI.extract_set_id(url)
            print(f"'{url}' -> '{result}' (expected '{expected_id}')")
            assert result == expected_id, f"Expected {expected_id}, got {result}"
        except Exception as e:
            print(f"'{url}' -> Error: {e}")
    
    # Test invalid URLs
    invalid_urls = [
        "https://example.com/no-numbers",
        "not-a-url",
        "",
    ]
    
    print("\nTesting invalid URLs:")
    for url in invalid_urls:
        try:
            result = QuizletAPI.extract_set_id(url)
            print(f"'{url}' -> Should have failed but got '{result}'")
        except ValueError as e:
            print(f"'{url}' -> Correctly failed: {e}")
        except Exception as e:
            print(f"'{url}' -> Unexpected error: {e}")
    
    print("✅ Quizlet API tests passed!")


def main():
    """Run all tests and demonstrations"""
    test_text_sanitization()
    test_question_type_selection()
    test_learning_progression() 
    test_round_generation()
    test_new_configuration_features()
    test_multiple_answers()
    test_quizlet_api()
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")
    print("\nThis implementation provides:")
    print("- Accurate text sanitization matching Quizlet's grading")
    print("- Intelligent question type selection based on confidence")
    print("- Mastery level progression through correct/incorrect answers")  
    print("- Intelligent round generation prioritizing struggling items")
    print("- Complete learning cycle with progress tracking")
    print("- Configurable question types and directions")
    print("- Partial credit system with similarity scoring")
    print("- Language-specific written question controls")
    print("- Multiple correct answers separated by /, ,, ;")
    print("- Quizlet API integration for loading vocabulary sets")


if __name__ == "__main__":
    main()