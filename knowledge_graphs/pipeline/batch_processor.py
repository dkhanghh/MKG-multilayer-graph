"""
Batch processor for handling large numbers of files.

This module provides functionality to process files in batches to avoid
memory issues and improve reliability when dealing with large datasets.
"""

import logging
import time
from typing import Dict, Any, List
from pathlib import Path

from .langgraph_executor import PipelineWorkflow
from ..models.pipeline_state import PipelineStateManager, PipelineMetrics

logger = logging.getLogger(__name__)


class BatchPipelineProcessor:
    """
    Process files in batches to avoid memory issues and improve reliability.

    Instead of processing all files at once, this processor:
    1. Scans all files
    2. Splits them into batches
    3. Processes each batch separately
    4. Aggregates results
    """

    def __init__(self, config: Dict[str, Any], batch_size: int = 10):
        """
        Initialize batch processor.

        Args:
            config: Pipeline configuration
            batch_size: Number of files to process per batch (default: 10)
        """
        self.config = config
        self.batch_size = batch_size
        self.workflow = PipelineWorkflow(config=config)

        logger.info(f"Initialized batch processor with batch_size={batch_size}")

    def process_directory_in_batches(
        self,
        input_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process all files in a directory in batches.

        Args:
            input_path: Path to directory containing files
            **kwargs: Additional parameters

        Returns:
            Aggregated results from all batches
        """
        input_dir = Path(input_path)

        if not input_dir.is_dir():
            # If it's a single file, just process it normally
            logger.info(f"Input is a single file, processing without batching")
            return self.workflow.run_pipeline(input_path, **kwargs)

        # Get all files to process
        all_files = self._get_files_from_directory(input_dir)

        if not all_files:
            logger.warning(f"No files found in {input_path}")
            return {
                "pipeline_id": "batch-empty",
                "status": "completed",
                "input_path": input_path,
                "output_path": None,
                "metrics": PipelineMetrics(),
                "errors": [],
                "execution_summary": {
                    "files_found": 0,
                    "files_processed": 0,
                    "batches": 0
                }
            }

        logger.info(f"Found {len(all_files)} files to process in {len(all_files) // self.batch_size + 1} batches")

        # Split into batches
        batches = self._create_batches(all_files)

        # Process each batch
        all_results = []
        aggregated_metrics = PipelineMetrics()
        all_errors = []

        start_time = time.time()

        for batch_num, batch_files in enumerate(batches, 1):
            logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch_files)} files)")

            batch_result = self._process_batch(
                batch_files,
                batch_num,
                **kwargs
            )

            all_results.append(batch_result)

            # Aggregate metrics
            if batch_result.get("metrics"):
                self._merge_metrics(aggregated_metrics, batch_result["metrics"])

            # Collect errors
            if batch_result.get("errors"):
                all_errors.extend(batch_result["errors"])

            logger.info(
                f"Batch {batch_num}/{len(batches)} completed. "
                f"Nodes: {batch_result.get('execution_summary', {}).get('total_nodes', 0)}, "
                f"Edges: {batch_result.get('execution_summary', {}).get('total_edges', 0)}"
            )

        total_time = time.time() - start_time
        aggregated_metrics.total_execution_time = total_time

        # Create final aggregated result
        final_result = {
            "pipeline_id": f"batch-{all_results[0]['pipeline_id']}" if all_results else "batch-unknown",
            "status": "completed" if not all_errors else "completed_with_errors",
            "input_path": input_path,
            "output_path": all_results[-1].get("output_path") if all_results else None,
            "metrics": aggregated_metrics,
            "errors": all_errors,
            "execution_summary": {
                "total_files": len(all_files),
                "files_processed": sum(r.get("execution_summary", {}).get("files_processed", 0) for r in all_results),
                "batches_processed": len(batches),
                "batch_size": self.batch_size,
                "total_nodes": sum(r.get("execution_summary", {}).get("total_nodes", 0) for r in all_results),
                "total_edges": sum(r.get("execution_summary", {}).get("total_edges", 0) for r in all_results),
                "total_execution_time": total_time,
                "batch_results": all_results
            }
        }

        logger.info(
            f"All batches completed! "
            f"Total files: {len(all_files)}, "
            f"Batches: {len(batches)}, "
            f"Total nodes: {final_result['execution_summary']['total_nodes']}, "
            f"Total edges: {final_result['execution_summary']['total_edges']}, "
            f"Time: {total_time:.2f}s"
        )

        return final_result

    def _get_files_from_directory(self, directory: Path) -> List[str]:
        """
        Get list of files from directory.

        Args:
            directory: Directory path

        Returns:
            List of file paths
        """
        # Get supported extensions from config
        scanner_config = self.config.get("pipeline", {}).get("components", {}).get("scanner", {}).get("config", {})
        supported_extensions = scanner_config.get("supported_extensions", [".pdf", ".txt", ".docx", ".md"])

        files = []
        for ext in supported_extensions:
            files.extend(directory.glob(f"*{ext}"))

        # Sort for consistent ordering
        files.sort()

        return [str(f) for f in files]

    def _create_batches(self, files: List[str]) -> List[List[str]]:
        """
        Split files into batches.

        Args:
            files: List of file paths

        Returns:
            List of batches (each batch is a list of file paths)
        """
        batches = []
        for i in range(0, len(files), self.batch_size):
            batch = files[i:i + self.batch_size]
            batches.append(batch)

        return batches

    def _process_batch(
        self,
        batch_files: List[str],
        batch_num: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a single batch of files.

        Args:
            batch_files: List of file paths in this batch
            batch_num: Batch number (for logging)
            **kwargs: Additional parameters

        Returns:
            Results from processing this batch
        """
        try:
            # For a batch, we need to process each file separately
            # and aggregate the subgraphs
            from ..models.graph import SubGraph
            from ..models.pipeline_state import PipelineState
            import uuid

            all_subgraphs = []
            batch_metrics = PipelineMetrics()
            batch_errors = []
            output_path = None

            for file_idx, file_path in enumerate(batch_files, 1):
                logger.info(f"  Processing file {file_idx}/{len(batch_files)}: {Path(file_path).name}")

                try:
                    # Process single file
                    result = self.workflow.run_pipeline(file_path, **kwargs)

                    # Extract subgraphs from result
                    if result.get("execution_summary"):
                        # Merge metrics
                        if result.get("metrics"):
                            self._merge_metrics(batch_metrics, result["metrics"])

                        # Track output path (use last one)
                        if result.get("output_path"):
                            output_path = result["output_path"]

                    # Collect any errors
                    if result.get("errors"):
                        batch_errors.extend(result["errors"])

                except Exception as e:
                    logger.error(f"  Error processing {file_path}: {e}")
                    batch_errors.append(f"File {Path(file_path).name}: {str(e)}")

            return {
                "pipeline_id": str(uuid.uuid4()),
                "status": "completed" if not batch_errors else "completed_with_errors",
                "batch_number": batch_num,
                "batch_files": [str(Path(f).name) for f in batch_files],
                "output_path": output_path,
                "metrics": batch_metrics,
                "errors": batch_errors,
                "execution_summary": {
                    "files_processed": len(batch_files),
                    "total_nodes": batch_metrics.total_nodes_extracted,
                    "total_edges": batch_metrics.total_edges_extracted,
                    "execution_time": sum(batch_metrics.component_times.values())
                }
            }

        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            return {
                "pipeline_id": str(uuid.uuid4()),
                "status": "failed",
                "batch_number": batch_num,
                "batch_files": [str(Path(f).name) for f in batch_files],
                "output_path": None,
                "metrics": PipelineMetrics(),
                "errors": [f"Batch {batch_num} failed: {str(e)}"],
                "execution_summary": {
                    "files_processed": 0,
                    "total_nodes": 0,
                    "total_edges": 0
                }
            }

    def _merge_metrics(
        self,
        target: PipelineMetrics,
        source: Any
    ) -> None:
        """
        Merge metrics from source into target.

        Args:
            target: Target metrics object to merge into
            source: Source metrics (can be dict or PipelineMetrics)
        """
        if isinstance(source, dict):
            target.total_files_processed += source.get("total_files_processed", 0)
            target.total_chunks_created += source.get("total_chunks_created", 0)
            target.total_nodes_extracted += source.get("total_nodes_extracted", 0)
            target.total_edges_extracted += source.get("total_edges_extracted", 0)
            target.total_subgraphs_created += source.get("total_subgraphs_created", 0)
        elif hasattr(source, 'total_files_processed'):
            target.total_files_processed += source.total_files_processed
            target.total_chunks_created += source.total_chunks_created
            target.total_nodes_extracted += source.total_nodes_extracted
            target.total_edges_extracted += source.total_edges_extracted
            target.total_subgraphs_created += source.total_subgraphs_created


def process_directory_in_batches(
    input_path: str,
    config: Dict[str, Any],
    batch_size: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to process a directory in batches.

    Args:
        input_path: Path to directory or file
        config: Pipeline configuration
        batch_size: Number of files per batch (default: 10)
        **kwargs: Additional parameters

    Returns:
        Aggregated results
    """
    processor = BatchPipelineProcessor(config, batch_size=batch_size)
    return processor.process_directory_in_batches(input_path, **kwargs)
