"""
DeepEval checkpoint helper for resumable evaluation.
Handles failures gracefully and allows resuming from last successful batch.
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any
from deepeval import evaluate
from deepeval.test_case import LLMTestCase


def save_evaluation_checkpoint(
    checkpoint_file: str,
    results: List[Dict[str, Any]],
    last_index: int,
    completed: bool = False
):
    """Save evaluation results checkpoint."""
    checkpoint_data = {
        'results': results,
        'last_index': last_index,
        'completed': completed
    }

    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    print(f"💾 Evaluation checkpoint saved: {last_index} test cases completed")


def load_evaluation_checkpoint(checkpoint_file: str) -> tuple:
    """Load evaluation checkpoint if exists."""
    checkpoint_path = Path(checkpoint_file)

    if not checkpoint_path.exists():
        print(f"ℹ️  No evaluation checkpoint found")
        return [], 0

    try:
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)

        results = checkpoint_data.get('results', [])
        last_index = checkpoint_data.get('last_index', 0)

        print(f"✅ Evaluation checkpoint loaded: {last_index} test cases already completed")
        return results, last_index

    except Exception as e:
        print(f"⚠️  Could not load checkpoint: {e}")
        return [], 0


def evaluate_with_checkpoint(
    test_cases: List[LLMTestCase],
    metrics: List[Any],
    checkpoint_file: str = "deepeval_checkpoint.json",
    batch_size: int = 10,
    # print_results: bool = True
):
    """
    Evaluate test cases with checkpoint support.

    Args:
        test_cases: List of LLMTestCase objects
        metrics: List of DeepEval metrics
        checkpoint_file: Path to checkpoint file
        batch_size: Number of test cases to evaluate per batch
        print_results: Whether to print results

    Returns:
        Evaluation results
    """
    # Load existing checkpoint
    completed_results, start_idx = load_evaluation_checkpoint(checkpoint_file)

    total_cases = len(test_cases)

    print(f"\n{'='*70}")
    print(f"DeepEval Evaluation with Checkpointing")
    print(f"{'='*70}")
    print(f"Total test cases: {total_cases}")
    print(f"Starting from: {start_idx}")
    print(f"Remaining: {total_cases - start_idx}")
    print(f"Batch size: {batch_size}")
    print(f"Checkpoint: {checkpoint_file}")
    print(f"{'='*70}\n")

    all_results = completed_results

    # Process in batches
    for batch_start in range(start_idx, total_cases, batch_size):
        batch_end = min(batch_start + batch_size, total_cases)
        batch_cases = test_cases[batch_start:batch_end]

        print(f"\n{'─'*70}")
        print(f"Evaluating batch {batch_start + 1}-{batch_end} / {total_cases}")
        print(f"{'─'*70}")

        try:
            # Evaluate batch
            batch_result = evaluate(
                test_cases=batch_cases,
                metrics=metrics,
                # print_results=print_results
            )

            # Save batch results
            # Note: DeepEval's evaluate() returns test results
            # We'll extract the relevant information
            batch_results_dict = {
                'batch_start': batch_start,
                'batch_end': batch_end,
                'success': True
            }
            all_results.append(batch_results_dict)

            # Save checkpoint after each batch
            save_evaluation_checkpoint(
                checkpoint_file,
                all_results,
                batch_end,
                completed=(batch_end >= total_cases)
            )

            print(f"✅ Batch {batch_start + 1}-{batch_end} completed successfully")

        except Exception as e:
            print(f"\n❌ Error evaluating batch {batch_start + 1}-{batch_end}: {e}")
            print(f"💾 Progress saved. You can resume by running this cell again.")

            # Save checkpoint with error info
            error_result = {
                'batch_start': batch_start,
                'batch_end': batch_end,
                'success': False,
                'error': str(e)
            }
            all_results.append(error_result)
            save_evaluation_checkpoint(checkpoint_file, all_results, batch_start)

            # Re-raise the error if you want to stop, or continue to next batch
            raise

    print(f"\n{'='*70}")
    print(f"✅ Evaluation Complete!")
    print(f"{'='*70}")
    print(f"Total batches processed: {len(all_results)}")
    print(f"Total test cases: {total_cases}")
    print(f"{'='*70}\n")

    return batch_result  # Return the last batch result


def evaluate_with_individual_checkpoint(
    test_cases: List[LLMTestCase],
    metrics: List[Any],
    checkpoint_file: str = "deepeval_individual_checkpoint.json",
    # print_results: bool = False
):
    """
    Evaluate test cases one by one with checkpoint after each case.
    Most granular checkpoint strategy - slower but safest.

    Args:
        test_cases: List of LLMTestCase objects
        metrics: List of DeepEval metrics
        checkpoint_file: Path to checkpoint file
        print_results: Whether to print individual results

    Returns:
        List of individual evaluation results
    """
    # Load existing checkpoint
    completed_indices, start_idx = load_evaluation_checkpoint(checkpoint_file)

    total_cases = len(test_cases)

    print(f"\n{'='*70}")
    print(f"DeepEval Individual Evaluation with Checkpointing")
    print(f"{'='*70}")
    print(f"Total test cases: {total_cases}")
    print(f"Starting from: {start_idx}")
    print(f"Remaining: {total_cases - start_idx}")
    print(f"Checkpoint: {checkpoint_file}")
    print(f"{'='*70}\n")

    results = completed_indices

    # Process one by one
    for i in range(start_idx, total_cases):
        test_case = test_cases[i]

        print(f"\nEvaluating test case {i + 1}/{total_cases}...")
        print(f"Input: {test_case.input[:60]}{'...' if len(test_case.input) > 60 else ''}")

        try:
            # Evaluate single test case
            result = evaluate(
                test_cases=[test_case],
                metrics=metrics,
                # print_results=print_results
            )

            results.append({
                'index': i,
                'success': True,
                'input': test_case.input[:100]
            })

            # Save checkpoint after each case
            save_evaluation_checkpoint(
                checkpoint_file,
                results,
                i + 1,
                completed=(i + 1 >= total_cases)
            )

            if (i + 1) % 10 == 0:
                print(f"✅ Progress: {i + 1}/{total_cases} completed")

        except Exception as e:
            print(f"\n❌ Error on test case {i + 1}: {e}")

            results.append({
                'index': i,
                'success': False,
                'error': str(e),
                'input': test_case.input[:100]
            })

            # Save checkpoint with error
            save_evaluation_checkpoint(checkpoint_file, results, i + 1)

            print(f"💾 Progress saved. You can resume by running this cell again.")

            # Continue to next test case instead of failing entire evaluation
            continue

    print(f"\n{'='*70}")
    print(f"✅ Individual Evaluation Complete!")
    print(f"{'='*70}")

    # Count successes and failures
    successes = sum(1 for r in results if r.get('success', False))
    failures = len(results) - successes

    print(f"Total: {total_cases}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"Success rate: {(successes/total_cases)*100:.1f}%")
    print(f"{'='*70}\n")

    return results
