"""
Robust evaluation helpers with retry logic and checkpointing.
Use these functions in your Jupyter notebook to handle API errors gracefully.
"""
import time
import json
from pathlib import Path
from typing import Tuple, List
from json.decoder import JSONDecodeError
from tqdm import tqdm


def safe_answer_with_retry(
    my_rag,
    question: str,
    max_retries: int = 3,
    base_delay: int = 5,
    max_delay: int = 60
) -> Tuple[str, List[str]]:
    """
    Safely call my_rag.answer with exponential backoff retry logic.

    This function handles:
    - JSONDecodeError (rate limiting, malformed responses)
    - Connection errors
    - Timeout errors
    - General exceptions

    Args:
        my_rag: MultilayerGraphRAG instance
        question: Question to answer
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 5)
        max_delay: Maximum delay between retries (default: 60)

    Returns:
        Tuple of (answer, retrieval_contexts)
        On failure: (error_message, [])
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Attempt to call the answer method
            answer, retrieval = my_rag.answer(question, return_retrieved_text=True)

            # Success!
            if attempt > 0:
                print(f"✅ Success after {attempt + 1} attempts")

            return answer, retrieval

        except JSONDecodeError as e:
            # Most common error: API returned HTML or non-JSON response
            last_error = e
            error_msg = f"JSONDecodeError: API returned non-JSON response"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")
            print(f"   Details: {str(e)[:100]}")

        except ConnectionError as e:
            # Network/connection issues
            last_error = e
            error_msg = f"ConnectionError: Network issue"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        except TimeoutError as e:
            # Request timeout
            last_error = e
            error_msg = f"TimeoutError: Request timed out"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        except Exception as e:
            # Catch-all for other errors
            last_error = e
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)[:100]}"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        # Calculate delay with exponential backoff
        if attempt < max_retries - 1:
            # Exponential backoff: 5s, 10s, 20s, 40s (capped at max_delay)
            delay = min(base_delay * (2 ** attempt), max_delay)
            print(f"⏳ Waiting {delay} seconds before retry...")
            time.sleep(delay)
        else:
            # Max retries exceeded
            final_error_msg = f"Error after {max_retries} attempts: {type(last_error).__name__}"
            print(f"❌ Failed after {max_retries} attempts. Last error: {type(last_error).__name__}")
            return final_error_msg, []

    # Should not reach here, but just in case
    return f"Error: Max retries exceeded - {type(last_error).__name__}", []


def load_checkpoint(checkpoint_file: str) -> Tuple[List, List, int]:
    """
    Load progress from checkpoint file.

    Args:
        checkpoint_file: Path to checkpoint JSON file

    Returns:
        Tuple of (retrieval_list, answer_list, start_index)
    """
    checkpoint_path = Path(checkpoint_file)

    if not checkpoint_path.exists():
        print(f"ℹ️  No checkpoint found at {checkpoint_file}")
        print(f"   Starting from beginning")
        return [], [], 0

    try:
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)

        retrieval_list = checkpoint_data.get('retrieval_list', [])
        answer_list = checkpoint_data.get('answer_list', [])
        start_idx = checkpoint_data.get('last_index', len(answer_list))

        print(f"✅ Checkpoint loaded from {checkpoint_file}")
        print(f"   Progress: {start_idx} questions already processed")

        return retrieval_list, answer_list, start_idx

    except json.JSONDecodeError as e:
        print(f"⚠️  Checkpoint file is corrupted: {e}")
        print(f"   Starting from beginning")
        return [], [], 0

    except Exception as e:
        print(f"⚠️  Could not load checkpoint: {e}")
        print(f"   Starting from beginning")
        return [], [], 0


def save_checkpoint(
    checkpoint_file: str,
    retrieval_list: List,
    answer_list: List,
    current_index: int,
    completed: bool = False
) -> bool:
    """
    Save progress to checkpoint file.

    Args:
        checkpoint_file: Path to checkpoint JSON file
        retrieval_list: List of retrieval contexts
        answer_list: List of answers
        current_index: Current question index
        completed: Whether processing is complete

    Returns:
        True if save succeeded, False otherwise
    """
    checkpoint_data = {
        'retrieval_list': retrieval_list,
        'answer_list': answer_list,
        'last_index': current_index,
        'completed': completed,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️  Could not save checkpoint: {e}")
        return False


def process_questions_robust(
    my_rag,
    question_list: List[str],
    checkpoint_file: str = "evaluation_progress.json",
    checkpoint_interval: int = 5,
    request_delay: int = 3,
    max_retries: int = 3
) -> Tuple[List, List]:
    """
    Process questions with robust error handling and checkpointing.

    Features:
    - Automatic checkpoint loading and saving
    - Exponential backoff retry logic
    - Progress tracking with tqdm
    - Detailed error reporting

    Args:
        my_rag: MultilayerGraphRAG instance
        question_list: List of questions to process
        checkpoint_file: Path to checkpoint file (default: "evaluation_progress.json")
        checkpoint_interval: Save checkpoint every N questions (default: 5)
        request_delay: Delay between successful requests in seconds (default: 3)
        max_retries: Maximum retries per question (default: 3)

    Returns:
        Tuple of (retrieval_list, answer_list)
    """
    # Load existing checkpoint
    retrieval_list, answer_list, start_idx = load_checkpoint(checkpoint_file)

    total_questions = len(question_list)

    print(f"\n{'='*70}")
    print(f"Starting evaluation with robust error handling")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Starting from: {start_idx}")
    print(f"Remaining: {total_questions - start_idx}")
    print(f"Checkpoint: {checkpoint_file} (saves every {checkpoint_interval} questions)")
    print(f"Request delay: {request_delay}s between requests")
    print(f"Max retries: {max_retries} per question")
    print(f"{'='*70}\n")

    # Track statistics
    success_count = start_idx
    error_count = 0

    # Process remaining questions
    for i, question in enumerate(tqdm(
        question_list[start_idx:],
        desc="Processing questions",
        initial=start_idx,
        total=total_questions
    )):
        actual_idx = start_idx + i

        print(f"\n{'─'*70}")
        print(f"Question {actual_idx + 1}/{total_questions}")
        print(f"{'─'*70}")
        print(f"Q: {question[:80]}{'...' if len(question) > 80 else ''}")

        # Call with retry logic
        answer, retrieval = safe_answer_with_retry(
            my_rag,
            question,
            max_retries=max_retries
        )

        # Track success/error
        if answer.startswith("Error"):
            error_count += 1
        else:
            success_count += 1

        retrieval_list.append(retrieval)
        answer_list.append(answer)

        # Save checkpoint periodically
        if (actual_idx + 1) % checkpoint_interval == 0:
            if save_checkpoint(checkpoint_file, retrieval_list, answer_list, actual_idx + 1):
                print(f"💾 Checkpoint saved: {actual_idx + 1}/{total_questions} questions")

        # Delay between requests (except for last question)
        if actual_idx < total_questions - 1:
            time.sleep(request_delay)

    # Save final checkpoint
    if save_checkpoint(checkpoint_file, retrieval_list, answer_list, total_questions, completed=True):
        print(f"\n{'='*70}")
        print(f"✅ Final checkpoint saved")
        print(f"{'='*70}")

    # Print final statistics
    print(f"\n{'='*70}")
    print(f"Evaluation Complete!")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Success rate: {(success_count/total_questions)*100:.1f}%")
    print(f"{'='*70}\n")

    return retrieval_list, answer_list


def safe_retrieve_with_retry(
    my_rag,
    question: str,
    top_k: int = 5,
    max_retries: int = 3,
    base_delay: int = 5,
    max_delay: int = 60
) -> List[str]:
    """
    Safely call my_rag.retrieve with exponential backoff retry logic.

    This function handles:
    - JSONDecodeError (rate limiting, malformed responses)
    - Connection errors
    - Timeout errors
    - General exceptions

    Args:
        my_rag: MultilayerGraphRAG instance
        question: Question to retrieve contexts for
        top_k: Number of contexts to retrieve (default: 5)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 5)
        max_delay: Maximum delay between retries (default: 60)

    Returns:
        List of retrieved context strings
        On failure: [error_message]
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Attempt to call the retrieve method
            retrieval = my_rag.retrieve(question, top_k)

            # Success!
            if attempt > 0:
                print(f"✅ Success after {attempt + 1} attempts")

            return retrieval

        except JSONDecodeError as e:
            # Most common error: API returned HTML or non-JSON response
            last_error = e
            error_msg = f"JSONDecodeError: API returned non-JSON response"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")
            print(f"   Details: {str(e)[:100]}")

        except ConnectionError as e:
            # Network/connection issues
            last_error = e
            error_msg = f"ConnectionError: Network issue"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        except TimeoutError as e:
            # Request timeout
            last_error = e
            error_msg = f"TimeoutError: Request timed out"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        except Exception as e:
            # Catch-all for other errors
            last_error = e
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)[:100]}"
            print(f"\n❌ [Attempt {attempt + 1}/{max_retries}] {error_msg}")

        # Calculate delay with exponential backoff
        if attempt < max_retries - 1:
            # Exponential backoff: 5s, 10s, 20s, 40s (capped at max_delay)
            delay = min(base_delay * (2 ** attempt), max_delay)
            print(f"⏳ Waiting {delay} seconds before retry...")
            time.sleep(delay)
        else:
            # Max retries exceeded
            final_error_msg = f"Error after {max_retries} attempts: {type(last_error).__name__}"
            print(f"❌ Failed after {max_retries} attempts. Last error: {type(last_error).__name__}")
            return [final_error_msg]

    # Should not reach here, but just in case
    return [f"Error: Max retries exceeded - {type(last_error).__name__}"]


def process_retrieval_robust(
    my_rag,
    question_list: List[str],
    top_k: int = 5,
    checkpoint_file: str = "retrieval_progress.json",
    checkpoint_interval: int = 5,
    request_delay: int = 2,
    max_retries: int = 3
) -> List[List[str]]:
    """
    Process retrieval for questions with robust error handling and checkpointing.

    Features:
    - Automatic checkpoint loading and saving
    - Exponential backoff retry logic
    - Progress tracking with tqdm
    - Detailed error reporting
    - Resume from last successful retrieval

    Args:
        my_rag: MultilayerGraphRAG instance
        question_list: List of questions to process
        top_k: Number of contexts to retrieve per question (default: 5)
        checkpoint_file: Path to checkpoint file (default: "retrieval_progress.json")
        checkpoint_interval: Save checkpoint every N questions (default: 5)
        request_delay: Delay between successful requests in seconds (default: 2)
        max_retries: Maximum retries per question (default: 3)

    Returns:
        List of retrieval results (each is a list of context strings)
    """
    # Load existing checkpoint
    checkpoint_path = Path(checkpoint_file)

    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
            retrieval_list = checkpoint_data.get('retrieval_list', [])
            start_idx = checkpoint_data.get('last_index', len(retrieval_list))
            print(f"✅ Checkpoint loaded from {checkpoint_file}")
            print(f"   Progress: {start_idx} questions already processed")
        except Exception as e:
            print(f"⚠️  Could not load checkpoint: {e}")
            print(f"   Starting from beginning")
            retrieval_list, start_idx = [], 0
    else:
        print(f"ℹ️  No checkpoint found at {checkpoint_file}")
        print(f"   Starting from beginning")
        retrieval_list, start_idx = [], 0

    total_questions = len(question_list)

    print(f"\n{'='*70}")
    print(f"Starting retrieval with robust error handling")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Starting from: {start_idx}")
    print(f"Remaining: {total_questions - start_idx}")
    print(f"Top-k contexts: {top_k}")
    print(f"Checkpoint: {checkpoint_file} (saves every {checkpoint_interval} questions)")
    print(f"Request delay: {request_delay}s between requests")
    print(f"Max retries: {max_retries} per question")
    print(f"{'='*70}\n")

    # Track statistics
    success_count = start_idx
    error_count = 0

    # Process remaining questions
    for i, question in enumerate(tqdm(
        question_list[start_idx:],
        desc="Retrieving contexts",
        initial=start_idx,
        total=total_questions
    )):
        actual_idx = start_idx + i

        print(f"\n{'─'*70}")
        print(f"Question {actual_idx + 1}/{total_questions}")
        print(f"{'─'*70}")
        print(f"Q: {question[:80]}{'...' if len(question) > 80 else ''}")

        # Call with retry logic
        retrieval = safe_retrieve_with_retry(
            my_rag,
            question,
            top_k=top_k,
            max_retries=max_retries
        )

        # Track success/error
        if len(retrieval) == 1 and retrieval[0].startswith("Error"):
            error_count += 1
            print(f"❌ Retrieval failed for question {actual_idx + 1}")
        else:
            success_count += 1
            print(f"✅ Retrieved {len(retrieval)} contexts")

        retrieval_list.append(retrieval)

        # Save checkpoint periodically
        if (actual_idx + 1) % checkpoint_interval == 0:
            checkpoint_data = {
                'retrieval_list': retrieval_list,
                'last_index': actual_idx + 1,
                'completed': False,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            try:
                with open(checkpoint_file, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)
                print(f"💾 Checkpoint saved: {actual_idx + 1}/{total_questions} questions")
            except Exception as e:
                print(f"⚠️  Could not save checkpoint: {e}")

        # Delay between requests (except for last question)
        if actual_idx < total_questions - 1 and not (len(retrieval) == 1 and retrieval[0].startswith("Error")):
            time.sleep(request_delay)

    # Save final checkpoint
    checkpoint_data = {
        'retrieval_list': retrieval_list,
        'last_index': total_questions,
        'completed': True,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        print(f"\n{'='*70}")
        print(f"✅ Final checkpoint saved")
        print(f"{'='*70}")
    except Exception as e:
        print(f"⚠️  Could not save final checkpoint: {e}")

    # Print final statistics
    print(f"\n{'='*70}")
    print(f"Retrieval Complete!")
    print(f"{'='*70}")
    print(f"Total questions: {total_questions}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Success rate: {(success_count/total_questions)*100:.1f}%")
    print(f"{'='*70}\n")

    return retrieval_list
