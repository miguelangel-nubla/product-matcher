#!/usr/bin/env python3
"""
Standardized Benchmark Runner for Product Matching Strategies

This script provides a reproducible, CI-compatible testing framework for:
- Comparing strategy performance
- Measuring accuracy improvements/regressions
- Establishing baseline metrics
- Generating comprehensive reports

Usage:
    python benchmark_runner.py [--format json|table|ci] [--baseline baseline.json]
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.services.debug import DebugStepTracker
from app.services.matcher.data_preparation import DataPreparation
from app.services.matcher.strategies.fuzzy import FuzzyMatchingStrategy
from app.services.matcher.strategies.semantic import SemanticMatchingStrategy


@dataclass
class TestResult:
    """Result of a single test case."""

    test_id: str
    category: str
    difficulty: str
    query: str
    expected_product_id: str | None
    expected_confidence: float

    # Strategy results
    strategy_results: dict[str, dict[str, Any]]

    # Evaluation
    overall_success: bool
    best_strategy: str | None
    best_confidence: float
    execution_time_ms: float


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    metadata: dict[str, Any]
    test_results: list[TestResult]
    strategy_summaries: dict[str, dict[str, Any]]
    category_analysis: dict[str, dict[str, Any]]
    performance_metrics: dict[str, Any]
    baseline_comparison: dict[str, Any] | None = None


class BenchmarkRunner:
    """Runs standardized benchmarks for product matching strategies."""

    def __init__(self, dataset_path: str = "tests/benchmarks/test_dataset.yaml"):
        self.dataset_path = Path(dataset_path)
        self.data_prep = DataPreparation()

        # Strategy classes (lazy initialization)
        self.strategy_classes = {
            "semantic": SemanticMatchingStrategy,
            "fuzzy": FuzzyMatchingStrategy,
        }
        self.strategies = {}

        # Load test dataset
        print("📂 Loading test dataset...")
        with open(self.dataset_path, encoding="utf-8") as f:
            self.dataset = yaml.safe_load(f)
        print(f"✅ Loaded {len(self.dataset['test_cases'])} test cases")

    def _ensure_strategies_initialized(self):
        """Initialize strategies with progress reporting."""
        for strategy_name, strategy_class in self.strategy_classes.items():
            if strategy_name not in self.strategies:
                print(f"🔧 Initializing {strategy_name} strategy...")
                start_time = time.time()
                self.strategies[strategy_name] = strategy_class()
                init_time = time.time() - start_time
                print(f"✅ {strategy_name} ready ({init_time:.2f}s)")

    def run_single_test(self, test_case: dict[str, Any]) -> TestResult:
        """Run a single test case against all strategies."""
        test_id = test_case["id"]
        query = test_case["query"]
        expected = test_case["expected"]

        print(f"🧪 Running test {test_id}: {test_case['description']}")
        print(
            f"   Query: '{query}' | Category: {test_case['category']} | Difficulty: {test_case['difficulty']}"
        )

        # Prepare context
        debug = DebugStepTracker()
        try:
            context = self.data_prep.prepare_context(
                query,
                self.dataset["metadata"]["language"],
                {"type": self.dataset["metadata"]["backend"]},
                debug,
            )
        except Exception as e:
            print(f"  ❌ Context preparation failed: {e}")
            return self._create_failed_result(
                test_case, f"Context preparation failed: {e}"
            )

        strategy_results = {}
        overall_start = time.time()

        # Test each strategy
        for strategy_name, strategy in self.strategies.items():
            try:
                start_time = time.time()
                result = strategy.match(context, threshold=0.7, max_candidates=5)
                execution_time = (time.time() - start_time) * 1000

                strategy_results[strategy_name] = {
                    "success": result.success,
                    "matches": result.matches,
                    "execution_time_ms": execution_time,
                    "candidates_checked": result.candidates_checked,
                    "top_match_id": result.matches[0][0] if result.matches else None,
                    "top_confidence": result.matches[0][1] if result.matches else 0.0,
                }

                # Check if this strategy found the expected result
                if result.success and result.matches:
                    top_match_id = result.matches[0][0]
                    top_confidence = result.matches[0][1]

                    is_correct = (
                        expected.get("product_id")
                        and str(top_match_id) == str(expected["product_id"])
                        and top_confidence >= expected.get("confidence_threshold", 0.7)
                    )
                    strategy_results[strategy_name]["is_correct"] = is_correct

                    status = "✅" if is_correct else "❌"
                    print(
                        f"  {strategy_name:>8}: {status} {top_confidence:.3f} (ID: {top_match_id}) [{execution_time:.0f}ms]"
                    )
                else:
                    strategy_results[strategy_name]["is_correct"] = False
                    print(f"  {strategy_name:>8}: ❌ No match [{execution_time:.0f}ms]")

            except Exception as e:
                print(f"  {strategy_name:>8}: 💥 Error: {str(e)}")
                strategy_results[strategy_name] = {
                    "error": str(e),
                    "execution_time_ms": 0,
                    "is_correct": False,
                }

        total_execution_time = (time.time() - overall_start) * 1000

        # Determine overall success and best strategy
        successful_strategies = [
            (name, result)
            for name, result in strategy_results.items()
            if result.get("is_correct", False)
        ]

        if successful_strategies:
            # Find strategy with highest confidence among successful ones
            best_strategy_name, best_result = max(
                successful_strategies, key=lambda x: x[1].get("top_confidence", 0)
            )
            overall_success = True
            best_confidence = best_result["top_confidence"]
        else:
            # No strategy succeeded, find highest confidence overall
            valid_results = [
                (name, result)
                for name, result in strategy_results.items()
                if "error" not in result and result.get("top_confidence", 0) > 0
            ]

            if valid_results:
                best_strategy_name, best_result = max(
                    valid_results, key=lambda x: x[1].get("top_confidence", 0)
                )
                best_confidence = best_result["top_confidence"]
            else:
                best_strategy_name = None
                best_confidence = 0.0

            overall_success = False

        return TestResult(
            test_id=test_id,
            category=test_case["category"],
            difficulty=test_case["difficulty"],
            query=query,
            expected_product_id=expected.get("product_id"),
            expected_confidence=expected.get("confidence_threshold", 0.7),
            strategy_results=strategy_results,
            overall_success=overall_success,
            best_strategy=best_strategy_name,
            best_confidence=best_confidence,
            execution_time_ms=total_execution_time,
        )

    def _create_failed_result(
        self, test_case: dict[str, Any], error_msg: str
    ) -> TestResult:
        """Create a failed test result."""
        return TestResult(
            test_id=test_case["id"],
            category=test_case["category"],
            difficulty=test_case["difficulty"],
            query=test_case["query"],
            expected_product_id=test_case["expected"].get("product_id"),
            expected_confidence=test_case["expected"].get("confidence_threshold", 0.7),
            strategy_results={"error": error_msg},
            overall_success=False,
            best_strategy=None,
            best_confidence=0.0,
            execution_time_ms=0.0,
        )

    def run_full_benchmark(self) -> BenchmarkReport:
        """Run the complete benchmark suite."""
        print("🔬 RUNNING STANDARDIZED PRODUCT MATCHING BENCHMARK")
        print("=" * 80)

        # Initialize strategies with progress reporting
        print("🚀 Initializing matching strategies...")
        self._ensure_strategies_initialized()
        print()

        test_cases = self.dataset["test_cases"]
        total_tests = len(test_cases)
        print(f"Running {total_tests} test cases...")
        print()

        test_results = []
        start_time = time.time()

        for i, test_case in enumerate(test_cases, 1):
            # Progress indicator
            elapsed = time.time() - start_time
            if i > 1:
                avg_time_per_test = elapsed / (i - 1)
                estimated_remaining = avg_time_per_test * (total_tests - i + 1)
                progress_percent = ((i - 1) / total_tests) * 100
                print(
                    f"📊 Progress: {i-1}/{total_tests} ({progress_percent:.1f}%) | "
                    f"Elapsed: {elapsed:.1f}s | ETA: {estimated_remaining:.1f}s"
                )

            result = self.run_single_test(test_case)
            test_results.append(result)
            print()

        # Final timing
        total_elapsed = time.time() - start_time
        print(f"✅ Completed {total_tests} tests in {total_elapsed:.2f}s")
        print()

        # Generate comprehensive analysis
        return self._generate_report(test_results)

    def _generate_report(self, test_results: list[TestResult]) -> BenchmarkReport:
        """Generate comprehensive benchmark report."""

        # Strategy summaries
        strategy_summaries = {}
        for strategy_name in self.strategies.keys():
            correct_count = sum(
                1
                for result in test_results
                if result.strategy_results.get(strategy_name, {}).get(
                    "is_correct", False
                )
            )
            total_count = len(
                [
                    result
                    for result in test_results
                    if strategy_name in result.strategy_results
                    and "error" not in result.strategy_results[strategy_name]
                ]
            )

            execution_times = [
                result.strategy_results[strategy_name]["execution_time_ms"]
                for result in test_results
                if strategy_name in result.strategy_results
                and "execution_time_ms" in result.strategy_results[strategy_name]
            ]

            strategy_summaries[strategy_name] = {
                "accuracy": (correct_count / total_count * 100)
                if total_count > 0
                else 0.0,
                "correct_count": correct_count,
                "total_count": total_count,
                "avg_execution_time_ms": sum(execution_times) / len(execution_times)
                if execution_times
                else 0.0,
                "max_execution_time_ms": max(execution_times)
                if execution_times
                else 0.0,
                "min_execution_time_ms": min(execution_times)
                if execution_times
                else 0.0,
            }

        # Category analysis
        category_analysis = {}
        for category in set(result.category for result in test_results):
            category_results = [r for r in test_results if r.category == category]
            category_success_count = sum(
                1 for r in category_results if r.overall_success
            )

            category_analysis[category] = {
                "total_tests": len(category_results),
                "successful_tests": category_success_count,
                "success_rate": (category_success_count / len(category_results) * 100)
                if category_results
                else 0.0,
                "avg_confidence": sum(r.best_confidence for r in category_results)
                / len(category_results)
                if category_results
                else 0.0,
            }

        # Performance metrics
        performance_metrics = {
            "total_tests": len(test_results),
            "overall_success_rate": sum(1 for r in test_results if r.overall_success)
            / len(test_results)
            * 100,
            "avg_execution_time_ms": sum(r.execution_time_ms for r in test_results)
            / len(test_results),
            "total_execution_time_ms": sum(r.execution_time_ms for r in test_results),
        }

        # Metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "dataset_version": self.dataset["metadata"]["version"],
            "test_count": len(test_results),
            "strategies_tested": list(self.strategies.keys()),
        }

        return BenchmarkReport(
            metadata=metadata,
            test_results=test_results,
            strategy_summaries=strategy_summaries,
            category_analysis=category_analysis,
            performance_metrics=performance_metrics,
        )

    def save_baseline(self, report: BenchmarkReport, filepath: str):
        """Save benchmark report as baseline for future comparisons."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        print(f"Baseline saved to {filepath}")

    def compare_with_baseline(
        self, current_report: BenchmarkReport, baseline_path: str
    ) -> dict[str, Any]:
        """Compare current results with baseline."""
        try:
            with open(baseline_path, encoding="utf-8") as f:
                baseline_data = json.load(f)

            comparison = {
                "baseline_timestamp": baseline_data["metadata"]["timestamp"],
                "current_timestamp": current_report.metadata["timestamp"],
                "strategy_changes": {},
                "category_changes": {},
                "overall_change": {},
            }

            # Compare strategies
            for strategy_name in current_report.strategy_summaries.keys():
                if strategy_name in baseline_data["strategy_summaries"]:
                    baseline_accuracy = baseline_data["strategy_summaries"][
                        strategy_name
                    ]["accuracy"]
                    current_accuracy = current_report.strategy_summaries[strategy_name][
                        "accuracy"
                    ]

                    comparison["strategy_changes"][strategy_name] = {
                        "accuracy_change": current_accuracy - baseline_accuracy,
                        "baseline_accuracy": baseline_accuracy,
                        "current_accuracy": current_accuracy,
                    }

            # Compare overall performance
            baseline_overall = baseline_data["performance_metrics"][
                "overall_success_rate"
            ]
            current_overall = current_report.performance_metrics["overall_success_rate"]

            comparison["overall_change"] = {
                "success_rate_change": current_overall - baseline_overall,
                "baseline_success_rate": baseline_overall,
                "current_success_rate": current_overall,
            }

            return comparison

        except Exception as e:
            print(f"Warning: Could not load baseline from {baseline_path}: {e}")
            return None

    def print_report(self, report: BenchmarkReport, format_type: str = "table"):
        """Print benchmark report in specified format."""

        if format_type == "ci":
            self._print_ci_format(report)
        elif format_type == "json":
            print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
        else:
            self._print_table_format(report)

    def _print_table_format(self, report: BenchmarkReport):
        """Print human-readable table format."""
        print("\n📊 BENCHMARK RESULTS SUMMARY")
        print("=" * 80)

        # Strategy performance
        print("\nSTRATEGY PERFORMANCE:")
        print(
            f"{'Strategy':>10} {'Accuracy':>10} {'Correct':>8} {'Total':>6} {'Avg Time':>10}"
        )
        print("-" * 50)

        for strategy, summary in report.strategy_summaries.items():
            print(
                f"{strategy:>10} {summary['accuracy']:>8.1f}% "
                f"{summary['correct_count']:>6}/{summary['total_count']:>2} "
                f"{summary['avg_execution_time_ms']:>8.1f}ms"
            )

        # Category analysis
        print("\nCATEGORY ANALYSIS:")
        print(
            f"{'Category':>15} {'Success Rate':>12} {'Tests':>6} {'Avg Confidence':>15}"
        )
        print("-" * 54)

        for category, analysis in report.category_analysis.items():
            print(
                f"{category:>15} {analysis['success_rate']:>10.1f}% "
                f"{analysis['successful_tests']:>2}/{analysis['total_tests']:>2} "
                f"{analysis['avg_confidence']:>13.3f}"
            )

        # Overall metrics
        print("\nOVERALL PERFORMANCE:")
        print(f"  Total Tests: {report.performance_metrics['total_tests']}")
        print(
            f"  Success Rate: {report.performance_metrics['overall_success_rate']:.1f}%"
        )
        print(
            f"  Total Execution Time: {report.performance_metrics['total_execution_time_ms']:.0f}ms"
        )
        print(
            f"  Average per Test: {report.performance_metrics['avg_execution_time_ms']:.0f}ms"
        )

    def _print_ci_format(self, report: BenchmarkReport):
        """Print CI-friendly format for automated testing."""
        print("BENCHMARK_RESULTS_START")

        # Key metrics for CI
        overall_success = report.performance_metrics["overall_success_rate"]
        print(f"OVERALL_SUCCESS_RATE={overall_success:.1f}")

        for strategy, summary in report.strategy_summaries.items():
            accuracy = summary["accuracy"]
            avg_time = summary["avg_execution_time_ms"]
            print(f"{strategy.upper()}_ACCURACY={accuracy:.1f}")
            print(f"{strategy.upper()}_AVG_TIME_MS={avg_time:.1f}")

        print("BENCHMARK_RESULTS_END")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run product matching benchmark tests")
    parser.add_argument(
        "--format",
        choices=["table", "json", "ci"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--save-baseline", type=str, help="Save results as baseline to specified file"
    )
    parser.add_argument(
        "--compare-baseline", type=str, help="Compare results with baseline file"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="tests/benchmarks/test_dataset.yaml",
        help="Path to test dataset (default: tests/benchmarks/test_dataset.yaml)",
    )

    args = parser.parse_args()

    # Run benchmark
    runner = BenchmarkRunner(args.dataset)
    report = runner.run_full_benchmark()

    # Compare with baseline if requested
    if args.compare_baseline:
        comparison = runner.compare_with_baseline(report, args.compare_baseline)
        if comparison:
            report.baseline_comparison = comparison

    # Print results
    runner.print_report(report, args.format)

    # Save baseline if requested
    if args.save_baseline:
        runner.save_baseline(report, args.save_baseline)

    # Exit with error code if success rate is too low (for CI)
    if args.format == "ci":
        success_rate = report.performance_metrics["overall_success_rate"]
        if success_rate < 50.0:  # Configurable threshold
            exit(1)


if __name__ == "__main__":
    main()
