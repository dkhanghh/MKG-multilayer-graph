"""
CSV-specific batch processor for handling large CSV files.

This module provides functionality to process CSV files in row-based batches
to avoid memory issues when dealing with large datasets.
"""

import csv
import json
import logging
import time
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path

from .langgraph_executor import PipelineWorkflow
from ..models.pipeline_state import PipelineMetrics

logger = logging.getLogger(__name__)


class CSVBatchProcessor:
    """
    Process CSV files in row-based batches to avoid memory issues.

    Instead of loading all CSV rows at once, this processor:
    1. Reads the CSV file incrementally
    2. Splits rows into batches
    3. Creates temporary CSV files for each batch
    4. Processes each batch separately with the pipeline
    5. Aggregates results
    """

    def __init__(self, config: Dict[str, Any], batch_size: int = 100, enable_checkpointing: bool = True):
        """
        Initialize CSV batch processor.

        Args:
            config: Pipeline configuration
            batch_size: Number of CSV rows to process per batch (default: 100)
            enable_checkpointing: Enable checkpoint/resume functionality (default: True)
        """
        self.config = config
        self.batch_size = batch_size
        self.enable_checkpointing = enable_checkpointing
        self.workflow = PipelineWorkflow(config=config)

        logger.info(f"Initialized CSV batch processor with batch_size={batch_size} rows, checkpointing={enable_checkpointing}")

    def _get_checkpoint_path(self, output_dir: str) -> Path:
        """
        Get the path to the checkpoint file.

        Args:
            output_dir: Output directory

        Returns:
            Path to checkpoint file
        """
        return Path(output_dir) / "batch_checkpoint.json"

    def _load_checkpoint(self, output_dir: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint if it exists.

        Args:
            output_dir: Output directory

        Returns:
            Checkpoint data or None if no checkpoint exists
        """
        if not self.enable_checkpointing:
            return None

        checkpoint_path = self._get_checkpoint_path(output_dir)

        if not checkpoint_path.exists():
            logger.info("No checkpoint found - starting fresh")
            return None

        try:
            with open(checkpoint_path, 'r') as f:
                checkpoint = json.load(f)

            logger.info(
                f"✅ Checkpoint loaded: {checkpoint['completed_batches']}/{checkpoint['total_batches']} batches completed"
            )
            return checkpoint

        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return None

    def _save_checkpoint(
        self,
        output_dir: str,
        csv_path: str,
        total_batches: int,
        completed_batches: int,
        all_results: List[Dict[str, Any]],
        aggregated_metrics: PipelineMetrics,
        all_errors: List[str]
    ) -> None:
        """
        Save checkpoint after each batch.

        Args:
            output_dir: Output directory
            csv_path: Path to CSV file
            total_batches: Total number of batches
            completed_batches: Number of completed batches
            all_results: Results from all completed batches
            aggregated_metrics: Aggregated metrics
            all_errors: List of errors
        """
        if not self.enable_checkpointing:
            return

        checkpoint_path = self._get_checkpoint_path(output_dir)

        checkpoint_data = {
            "csv_path": csv_path,
            "total_batches": total_batches,
            "completed_batches": completed_batches,
            "batch_size": self.batch_size,
            "batch_results": all_results,
            "metrics": {
                "total_files_processed": aggregated_metrics.total_files_processed,
                "total_chunks_created": aggregated_metrics.total_chunks_created,
                "total_nodes_extracted": aggregated_metrics.total_nodes_extracted,
                "total_edges_extracted": aggregated_metrics.total_edges_extracted,
                "total_subgraphs_created": aggregated_metrics.total_subgraphs_created,
            },
            "errors": all_errors,
            "last_updated": time.time()
        }

        try:
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)

            logger.debug(f"💾 Checkpoint saved: {completed_batches}/{total_batches} batches")

        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def _delete_checkpoint(self, output_dir: str) -> None:
        """
        Delete checkpoint file after successful completion.

        Args:
            output_dir: Output directory
        """
        if not self.enable_checkpointing:
            return

        checkpoint_path = self._get_checkpoint_path(output_dir)

        try:
            if checkpoint_path.exists():
                checkpoint_path.unlink()
                logger.info("🗑️  Checkpoint deleted after successful completion")
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint: {e}")

    def process_csv_in_batches(
        self,
        csv_path: str,
        output_dir: str = "./output/csv_batches",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a large CSV file in row-based batches.

        Args:
            csv_path: Path to the CSV file
            output_dir: Directory for batch outputs (default: ./output/csv_batches)
            **kwargs: Additional parameters

        Returns:
            Aggregated results from all batches
        """
        csv_file = Path(csv_path)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        if not csv_file.suffix.lower() == '.csv':
            raise ValueError(f"File must be a CSV: {csv_path}")

        logger.info(f"Processing CSV file: {csv_path}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Read CSV and count total rows
        total_rows, headers = self._count_rows_and_get_headers(csv_path)

        if total_rows == 0:
            logger.warning(f"No data rows found in {csv_path}")
            return self._create_empty_result(csv_path, output_dir)

        num_batches = (total_rows + self.batch_size - 1) // self.batch_size
        logger.info(f"Found {total_rows} data rows to process in {num_batches} batches")

        # Load checkpoint if exists
        checkpoint = self._load_checkpoint(output_dir)

        if checkpoint:
            # Resume from checkpoint
            all_results = checkpoint.get("batch_results", [])
            all_errors = checkpoint.get("errors", [])
            start_batch_num = checkpoint.get("completed_batches", 0) + 1

            # Restore aggregated metrics
            aggregated_metrics = PipelineMetrics()
            checkpoint_metrics = checkpoint.get("metrics", {})
            aggregated_metrics.total_files_processed = checkpoint_metrics.get("total_files_processed", 0)
            aggregated_metrics.total_chunks_created = checkpoint_metrics.get("total_chunks_created", 0)
            aggregated_metrics.total_nodes_extracted = checkpoint_metrics.get("total_nodes_extracted", 0)
            aggregated_metrics.total_edges_extracted = checkpoint_metrics.get("total_edges_extracted", 0)
            aggregated_metrics.total_subgraphs_created = checkpoint_metrics.get("total_subgraphs_created", 0)

            logger.info(
                f"🔄 Resuming from batch {start_batch_num}/{num_batches} "
                f"(already completed: {len(all_results)} batches)"
            )
        else:
            # Start fresh
            all_results = []
            aggregated_metrics = PipelineMetrics()
            all_errors = []
            start_batch_num = 1

        start_time = time.time()

        # Create temporary directory for batch CSV files
        temp_dir = tempfile.mkdtemp(prefix="csv_batch_")

        try:
            # Read CSV and create batches
            batches = self._create_row_batches(csv_path, headers, temp_dir)

            # Process only remaining batches
            for batch_num in range(start_batch_num, len(batches) + 1):
                batch_info = batches[batch_num - 1]
                logger.info(
                    f"Processing batch {batch_num}/{len(batches)} "
                    f"(rows {batch_info['start_row']}-{batch_info['end_row']})"
                )

                batch_result = self._process_batch(
                    batch_info,
                    batch_num,
                    output_dir,
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
                    f"Rows: {batch_info['row_count']}, "
                    f"Nodes: {batch_result.get('execution_summary', {}).get('total_nodes', 0)}, "
                    f"Edges: {batch_result.get('execution_summary', {}).get('total_edges', 0)}"
                )

                # Save checkpoint after each batch
                self._save_checkpoint(
                    output_dir=output_dir,
                    csv_path=csv_path,
                    total_batches=len(batches),
                    completed_batches=batch_num,
                    all_results=all_results,
                    aggregated_metrics=aggregated_metrics,
                    all_errors=all_errors
                )

        finally:
            # Clean up temporary batch CSV files
            self._cleanup_temp_files(temp_dir)

        total_time = time.time() - start_time
        aggregated_metrics.total_execution_time = total_time

        # Create final aggregated result
        final_result = {
            "pipeline_id": f"csv-batch-{all_results[0]['pipeline_id']}" if all_results else "csv-batch-unknown",
            "status": "completed" if not all_errors else "completed_with_errors",
            "input_path": csv_path,
            "output_path": output_dir,
            "metrics": aggregated_metrics,
            "errors": all_errors,
            "execution_summary": {
                "total_rows": total_rows,
                "rows_processed": sum(r.get("execution_summary", {}).get("rows_processed", 0) for r in all_results),
                "batches_processed": len(batches),
                "batch_size": self.batch_size,
                "total_chunks": sum(r.get("execution_summary", {}).get("total_chunks", 0) for r in all_results),
                "total_nodes": sum(r.get("execution_summary", {}).get("total_nodes", 0) for r in all_results),
                "total_edges": sum(r.get("execution_summary", {}).get("total_edges", 0) for r in all_results),
                "total_execution_time": total_time,
                "batch_results": all_results
            }
        }

        logger.info(
            f"All batches completed! "
            f"Total rows: {total_rows}, "
            f"Batches: {len(batches)}, "
            f"Total nodes: {final_result['execution_summary']['total_nodes']}, "
            f"Total edges: {final_result['execution_summary']['total_edges']}, "
            f"Time: {total_time:.2f}s"
        )

        # Delete checkpoint after successful completion
        self._delete_checkpoint(output_dir)

        return final_result

    def _count_rows_and_get_headers(self, csv_path: str) -> tuple[int, List[str]]:
        """
        Count total rows and get headers from CSV.

        Args:
            csv_path: Path to CSV file

        Returns:
            Tuple of (row_count, headers)
        """
        encoding = self.config.get("pipeline", {}).get("components", {}).get(
            "reader", {}
        ).get("config", {}).get("encoding", "utf-8")

        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            row_count = sum(1 for _ in reader)

        return row_count, headers

    def _create_row_batches(
        self,
        csv_path: str,
        headers: List[str],
        temp_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Create temporary CSV files for each batch of rows.

        Args:
            csv_path: Path to original CSV file
            headers: CSV headers
            temp_dir: Temporary directory for batch files

        Returns:
            List of batch info dictionaries
        """
        encoding = self.config.get("pipeline", {}).get("components", {}).get(
            "reader", {}
        ).get("config", {}).get("encoding", "utf-8")

        batches = []
        batch_num = 0
        current_batch_rows = []
        start_row = 1  # Start counting from 1 (after header)

        with open(csv_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f)

            for row_idx, row in enumerate(reader, start=1):
                current_batch_rows.append(row)

                # When batch is full or last row
                if len(current_batch_rows) >= self.batch_size:
                    batch_num += 1
                    batch_file = self._create_batch_csv(
                        current_batch_rows,
                        headers,
                        batch_num,
                        temp_dir,
                        encoding
                    )

                    batches.append({
                        "batch_num": batch_num,
                        "batch_file": batch_file,
                        "start_row": start_row,
                        "end_row": row_idx,
                        "row_count": len(current_batch_rows)
                    })

                    current_batch_rows = []
                    start_row = row_idx + 1

            # Handle remaining rows in last batch
            if current_batch_rows:
                batch_num += 1
                batch_file = self._create_batch_csv(
                    current_batch_rows,
                    headers,
                    batch_num,
                    temp_dir,
                    encoding
                )

                batches.append({
                    "batch_num": batch_num,
                    "batch_file": batch_file,
                    "start_row": start_row,
                    "end_row": start_row + len(current_batch_rows) - 1,
                    "row_count": len(current_batch_rows)
                })

        return batches

    def _create_batch_csv(
        self,
        rows: List[Dict[str, Any]],
        headers: List[str],
        batch_num: int,
        temp_dir: str,
        encoding: str
    ) -> str:
        """
        Create a temporary CSV file for a batch of rows.

        Args:
            rows: List of row dictionaries
            headers: CSV headers
            batch_num: Batch number
            temp_dir: Temporary directory
            encoding: File encoding

        Returns:
            Path to created batch CSV file
        """
        batch_file = Path(temp_dir) / f"batch_{batch_num:04d}.csv"

        with open(batch_file, 'w', encoding=encoding, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        logger.debug(f"Created batch CSV: {batch_file} with {len(rows)} rows")
        return str(batch_file)

    def _process_batch(
        self,
        batch_info: Dict[str, Any],
        batch_num: int,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a single batch CSV file.

        Args:
            batch_info: Batch information dictionary
            batch_num: Batch number
            output_dir: Output directory
            **kwargs: Additional parameters

        Returns:
            Results from processing this batch
        """
        import uuid

        try:
            batch_file = batch_info["batch_file"]

            # Update output path for this batch
            batch_output_dir = f"{output_dir}/batch_{batch_num:04d}"

            # Update config for this batch
            batch_config = self.config.copy()
            if "pipeline" in batch_config and "components" in batch_config["pipeline"]:
                if "writer" in batch_config["pipeline"]["components"]:
                    if "config" not in batch_config["pipeline"]["components"]["writer"]:
                        batch_config["pipeline"]["components"]["writer"]["config"] = {}
                    batch_config["pipeline"]["components"]["writer"]["config"]["output_path"] = batch_output_dir

            # Create workflow with batch config
            batch_workflow = PipelineWorkflow(config=batch_config)

            # Process the batch CSV file
            result = batch_workflow.run_pipeline(batch_file, **kwargs)

            return {
                "pipeline_id": result.get("pipeline_id", str(uuid.uuid4())),
                "status": result.get("status", "completed"),
                "batch_number": batch_num,
                "start_row": batch_info["start_row"],
                "end_row": batch_info["end_row"],
                "row_count": batch_info["row_count"],
                "output_path": batch_output_dir,
                "metrics": result.get("metrics"),
                "errors": result.get("errors", []),
                "execution_summary": {
                    "rows_processed": batch_info["row_count"],
                    "total_chunks": result.get("execution_summary", {}).get("total_chunks", 0),
                    "total_nodes": result.get("execution_summary", {}).get("total_nodes", 0),
                    "total_edges": result.get("execution_summary", {}).get("total_edges", 0),
                    "execution_time": result.get("execution_summary", {}).get("total_execution_time", 0)
                }
            }

        except Exception as e:
            logger.error(f"Batch {batch_num} failed: {e}")
            return {
                "pipeline_id": str(uuid.uuid4()),
                "status": "failed",
                "batch_number": batch_num,
                "start_row": batch_info["start_row"],
                "end_row": batch_info["end_row"],
                "row_count": batch_info["row_count"],
                "output_path": None,
                "metrics": PipelineMetrics(),
                "errors": [f"Batch {batch_num} (rows {batch_info['start_row']}-{batch_info['end_row']}): {str(e)}"],
                "execution_summary": {
                    "rows_processed": 0,
                    "total_chunks": 0,
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

    def _cleanup_temp_files(self, temp_dir: str) -> None:
        """
        Clean up temporary batch CSV files.

        Args:
            temp_dir: Temporary directory to clean up
        """
        import shutil

        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    def _create_empty_result(self, csv_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Create an empty result for when no rows are found.

        Args:
            csv_path: Path to CSV file
            output_dir: Output directory

        Returns:
            Empty result dictionary
        """
        return {
            "pipeline_id": "csv-batch-empty",
            "status": "completed",
            "input_path": csv_path,
            "output_path": output_dir,
            "metrics": PipelineMetrics(),
            "errors": [],
            "execution_summary": {
                "total_rows": 0,
                "rows_processed": 0,
                "batches_processed": 0,
                "batch_size": self.batch_size,
                "total_chunks": 0,
                "total_nodes": 0,
                "total_edges": 0,
                "total_execution_time": 0
            }
        }


def process_csv_in_batches(
    csv_path: str,
    config: Dict[str, Any],
    batch_size: int = 100,
    output_dir: str = "./output/csv_batches",
    enable_checkpointing: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to process a CSV file in row-based batches.

    Args:
        csv_path: Path to CSV file
        config: Pipeline configuration
        batch_size: Number of rows per batch (default: 100)
        output_dir: Directory for batch outputs
        enable_checkpointing: Enable checkpoint/resume functionality (default: True)
        **kwargs: Additional parameters

    Returns:
        Aggregated results

    Example:
        >>> from knowledge_graphs.pipeline.csv_batch_processor import process_csv_in_batches
        >>> from knowledge_graphs.pipeline.config import load_config
        >>>
        >>> config = load_config("examples/config_vn30_csv.yaml")
        >>> results = process_csv_in_batches(
        ...     ".data/data_vn30_first_100.csv",
        ...     config,
        ...     batch_size=100
        ... )
        >>> print(f"Processed {results['execution_summary']['total_rows']} rows")

        # To resume from a failed run, just call again with same output_dir:
        >>> results = process_csv_in_batches(
        ...     ".data/data_vn30_first_100.csv",
        ...     config,
        ...     batch_size=100,
        ...     output_dir="./output/vn30_batches"  # Same output_dir as before
        ... )
    """
    processor = CSVBatchProcessor(config, batch_size=batch_size, enable_checkpointing=enable_checkpointing)
    return processor.process_csv_in_batches(csv_path, output_dir, **kwargs)
