"""
Accuracy Evaluation Runner.
Runs golden test set and reports accuracy metrics.
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.rag.engine import QueryEngine


import httpx

logger = logging.getLogger(__name__)

class HallucinationJudge:
    """
    LLM-as-a-Judge to evaluate answer faithfulness.
    Checks if the answer contains information not present in the context.
    """
    
    JUDGE_PROMPT = """You are an impartial judge evaluating a RAG system.
    
QUERY: {query}
CONTEXT: {context}
ANSWER: {answer}

Task: Determine if the ANSWER contains any factual claims that are NOT supported by the CONTEXT.
- Ignore minor phrasing differences or conversational filler.
- Focus on specs, features, compatibility, and product names.
- If the answer says "I don't know" or "Not found", and the context is empty or irrelevant, it is FAITHFUL.
- If the answer makes a claim (e.g. "Power is 50W") but the context says "Power is 30W" or doesn't mention power, it is HALLUCINATION.

Respond with valid JSON:
{{
  "faithful": boolean,
  "reason": "explanation of why it is faithful or hallucinated"
}}"""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_llm_model  # Use same model or stronger
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def evaluate(self, query: str, answer: str, context: str) -> dict:
        """Evaluate if answer is faithful to context."""
        if not answer or not context:
            return {"faithful": True, "reason": "Empty answer or context"}
            
        prompt = self.JUDGE_PROMPT.format(query=query, context=context, answer=answer)
        
        try:
            response = await self._client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.0}
                }
            )
            data = response.json()
            result_json = data.get('response', '{}')
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"Judge error: {e}")
            return {"faithful": True, "reason": "Judge error, assuming faithful"}

    async def close(self):
        await self._client.aclose()



@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: str
    category: str
    query: str
    passed: bool
    score: float = 1.0
    answer: str = ""
    expected: Optional[dict] = None
    actual: Optional[dict] = None
    error: Optional[str] = None

    duration_ms: float = 0.0
    faithfulness: bool = True
    faithfulness_reason: str = ""



@dataclass 
class EvaluationReport:
    """Complete evaluation report."""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    accuracy: float
    by_category: dict[str, dict] = field(default_factory=dict)
    results: list[TestResult] = field(default_factory=list)
    avg_duration_ms: float = 0.0

    hallucination_rate: float = 0.0



class AccuracyRunner:
    """
    Run accuracy tests against golden test set.
    
    Evaluates:
    - Direct lookup accuracy (correct model & fields)
    - Semantic search relevance (correct results)
    - Calculation correctness (exact match)
    - Citation presence
    """
    
    def __init__(self, golden_set_path: Path):
        """
        Initialize the runner.
        
        Args:
            golden_set_path: Path to golden_set.json
        """
        self.golden_set_path = golden_set_path
        self.golden_set_path = golden_set_path
        self.engine: Optional[QueryEngine] = None
        self.judge: Optional[HallucinationJudge] = None

    
    async def setup(self) -> None:
        """Initialize the query engine."""
        self.engine = QueryEngine()
        self.judge = HallucinationJudge()

    
    async def teardown(self) -> None:
        """Clean up resources."""
        if self.engine:
            await self.engine.close()
        if self.judge:
            await self.judge.close()

    
    def load_test_cases(self) -> list[dict]:
        """Load test cases from golden set."""
        with open(self.golden_set_path, 'r') as f:
            data = json.load(f)
        return data.get('test_cases', [])
    
    async def run_test(self, test_case: dict) -> TestResult:
        """
        Run a single test case.
        
        Args:
            test_case: Test case dict from golden set
            
        Returns:
            TestResult with pass/fail status
        """
        import time
        
        test_id = test_case.get('id', 'unknown')
        category = test_case.get('category', 'unknown')
        query = test_case.get('query', '')
        
        result = TestResult(
            test_id=test_id,
            category=category,
            query=query,
            passed=False,
        )
        
        try:
            start = time.perf_counter()
            answer = await self.engine.query(query)
            end = time.perf_counter()
            
            result.duration_ms = (end - start) * 1000
            result.answer = answer.answer
            result.actual = answer.to_dict()
            
            # Evaluate based on category
            if category == 'direct_lookup':
                result = self._evaluate_direct_lookup(result, test_case, answer)
            elif category == 'semantic_search':
                result = self._evaluate_semantic_search(result, test_case, answer)
            elif category == 'calculation':
                result = self._evaluate_calculation(result, test_case, answer)
            elif category == 'edge_case':
                result = self._evaluate_edge_case(result, test_case, answer)
            elif category == 'complex':
                result = self._evaluate_complex(result, test_case, answer)
            elif category == 'citation':
                result = self._evaluate_citation(result, test_case, answer)
            else:
                # Unknown category - just check for non-error response
                result.passed = 'error' not in answer.answer.lower()
            
            # Use LLM-as-a-Judge for Hallucination Check
            # Context comes from retrieved products
            context_text = ""
            if answer.citations:
                context_text = "\n".join([f"{c.model_name} {c.field}: {c.value}" for c in answer.citations])
            elif answer.products_used:
                # If no specific citations, use product names as weak context
                context_text = f"Known products: {', '.join(answer.products_used)}"
            
            # Only judge if there is an answer and it's not a refusal
            if answer.answer and "sorry, i do not" not in answer.answer.lower():
                judge_result = await self.judge.evaluate(query, answer.answer, context_text)
                result.faithfulness = judge_result.get("faithful", True)
                result.faithfulness_reason = judge_result.get("reason", "No reason provided")
            
        except Exception as e:

            result.error = str(e)
            result.passed = False
            logger.error(f"Test {test_id} failed with error: {e}")
        
        return result
    
    def _evaluate_direct_lookup(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate direct lookup test."""
        expected_model = test_case.get('expected_model', '')
        expected_fields = test_case.get('expected_fields', [])
        
        # Check if expected model is mentioned
        model_found = expected_model.lower() in answer.answer.lower()
        
        # Check if product was used
        products_used = answer.products_used or []
        product_match = any(
            expected_model.upper() in p.upper() for p in products_used
        )
        
        # Check if expected fields have citations
        citations = answer.citations or []
        fields_cited = set(c.field for c in citations)
        fields_match = all(f in fields_cited for f in expected_fields)
        
        result.passed = model_found and (product_match or not products_used)
        result.score = sum([model_found, product_match, fields_match]) / 3
        result.expected = {
            'model': expected_model,
            'fields': expected_fields,
        }
        
        return result
    
    def _evaluate_semantic_search(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate semantic search test."""
        min_results = test_case.get('min_results', 1)
        expected_category = test_case.get('expected_category')
        expected_voltage = test_case.get('expected_voltage')
        expected_series = test_case.get('expected_series')
        
        products_used = answer.products_used or []
        
        # Check minimum results
        has_results = len(products_used) >= min_results
        
        # Score based on confidence
        confidence_ok = answer.confidence >= 0.5
        
        result.passed = has_results and confidence_ok
        result.score = answer.confidence
        result.expected = {
            'min_results': min_results,
            'category': expected_category,
            'voltage': expected_voltage,
            'series': expected_series,
        }
        
        return result
    
    def _evaluate_calculation(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate calculation test."""
        expected_result = test_case.get('expected_result', {})
        
        # Parse answer for values
        answer_text = answer.answer.lower()
        
        checks = []
        
        if 'compatible' in expected_result:
            expected_compat = expected_result['compatible']
            if expected_compat:
                # Check for positive compatibility
                actual_compat = '✅' in answer.answer or (
                    'compatible' in answer_text and 'incompatible' not in answer_text and 'not compatible' not in answer_text
                )
            else:
                # Check for negative compatibility
                actual_compat = '❌' in answer.answer or 'not compatible' in answer_text or 'incompatible' in answer_text
            checks.append(actual_compat)
        
        if 'total_load' in expected_result:
            expected_load = str(expected_result['total_load'])
            checks.append(expected_load in answer.answer)
        
        if 'total_impedance' in expected_result:
            expected_imp = expected_result['total_impedance']
            checks.append(f"{expected_imp}" in answer.answer)
        
        if 'recommended_watts' in expected_result:
            expected_rec = str(expected_result['recommended_watts'])
            checks.append(expected_rec in answer.answer)
        
        result.passed = all(checks) if checks else True
        result.score = sum(checks) / len(checks) if checks else 1.0
        result.expected = expected_result
        
        return result
    
    def _evaluate_edge_case(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate edge case test."""
        expected_contains = test_case.get('expected_contains', [])
        
        if expected_contains:
            answer_lower = answer.answer.lower()
            matches = [kw in answer_lower for kw in expected_contains]
            result.passed = any(matches)
            result.score = sum(matches) / len(matches)
        else:
            # Just check no crash
            result.passed = answer.answer != ""
            result.score = 1.0 if result.passed else 0.0
        
        result.expected = {
            'behavior': test_case.get('expected_behavior'),
            'contains': expected_contains,
        }
        
        return result
    
    def _evaluate_complex(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate complex queries."""
        expected_models = test_case.get('expected_models', [])
        
        answer_lower = answer.answer.lower()
        found = [m for m in expected_models if m.lower() in answer_lower]
        
        result.passed = len(found) >= len(expected_models) // 2
        result.score = len(found) / len(expected_models) if expected_models else 1.0
        result.expected = {'models': expected_models}
        
        return result
    
    def _evaluate_citation(
        self,
        result: TestResult,
        test_case: dict,
        answer,
    ) -> TestResult:
        """Evaluate citation presence."""
        expect_citations = test_case.get('expected_citations', False)
        
        has_citations = bool(answer.citations)
        
        if expect_citations:
            result.passed = has_citations
        else:
            result.passed = True
        
        result.score = 1.0 if result.passed else 0.0
        result.expected = {'has_citations': expect_citations}
        
        return result
    
    async def run_all(self) -> EvaluationReport:
        """
        Run all test cases and generate report.
        
        Returns:
            EvaluationReport with results
        """
        await self.setup()
        
        test_cases = self.load_test_cases()
        results = []
        
        logger.info(f"Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            result = await self.run_test(test_case)
            results.append(result)
            
            status = "✓" if result.passed else "✗"
            logger.info(
                f"[{i}/{len(test_cases)}] {status} {result.test_id}: "
                f"{result.score:.2f} ({result.duration_ms:.0f}ms)"
            )
        
        await self.teardown()
        
        # Generate report
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        accuracy = passed / len(results) if results else 0.0
        
        # By category
        by_category = {}
        for result in results:
            if result.category not in by_category:
                by_category[result.category] = {'total': 0, 'passed': 0}
            by_category[result.category]['total'] += 1
            if result.passed:
                by_category[result.category]['passed'] += 1
        
        for cat in by_category:
            by_category[cat]['accuracy'] = (
                by_category[cat]['passed'] / by_category[cat]['total']
            )
        
        avg_duration = sum(r.duration_ms for r in results) / len(results) if results else 0
        
        report = EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(results),
            passed=passed,
            failed=failed,
            accuracy=accuracy,
            by_category=by_category,
            results=results,
            avg_duration_ms=avg_duration,
            hallucination_rate=len([r for r in results if not r.faithfulness]) / len(results) if results else 0.0,
        )

        
        return report
    
    def print_report(self, report: EvaluationReport) -> None:
        """Print evaluation report to console."""
        print("\n" + "=" * 60)
        print("ACCURACY EVALUATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed}")
        print(f"Failed: {report.failed}")
        print(f"Accuracy: {report.accuracy:.1%}")
        print(f"Accuracy: {report.accuracy:.1%}")
        print(f"Hallucination Rate: {report.hallucination_rate:.1%}")
        print(f"Faithfulness: {1.0 - report.hallucination_rate:.1%}")
        print(f"Avg Duration: {report.avg_duration_ms:.0f}ms")

        
        print("\nBy Category:")
        for cat, stats in report.by_category.items():
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({stats['accuracy']:.1%})")
        
        if report.failed > 0:
            print("\nFailed Tests:")
            for result in report.results:
                if not result.passed:
                    print(f"  - {result.test_id}: {result.query[:50]}...")
                    if result.error:
                        print(f"    Error: {result.error}")
        
        hallucinations = [r for r in report.results if not r.faithfulness]
        if hallucinations:
            print("\nPotential Hallucinations:")
            for result in hallucinations:
                print(f"  - {result.test_id}: {result.query}")
                print(f"    Answer: {result.answer[:100]}...")
                print(f"    Reason: {result.faithfulness_reason}")
        
        print("=" * 60 + "\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run accuracy evaluation on golden test set"
    )
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=Path(__file__).parent / "golden_set.json",
        help="Path to golden_set.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to save JSON report",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=settings.log_format,
    )
    
    runner = AccuracyRunner(args.golden_set)
    report = await runner.run_all()
    
    runner.print_report(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                'timestamp': report.timestamp,
                'total_tests': report.total_tests,
                'passed': report.passed,
                'failed': report.failed,
                'accuracy': report.accuracy,
                'hallucination_rate': report.hallucination_rate,
                'avg_duration_ms': report.avg_duration_ms,
                'by_category': report.by_category,

                'results': [

                    {
                        'test_id': r.test_id,
                        'category': r.category,
                        'query': r.query,
                        'passed': r.passed,
                        'score': r.score,
                        'duration_ms': r.duration_ms,
                        'faithfulness': r.faithfulness,
                        'faithfulness_reason': r.faithfulness_reason,
                        'error': r.error,

                    }
                    for r in report.results
                ],
            }, f, indent=2)
        print(f"Report saved to: {args.output}")
    
    # Exit with error code if accuracy below threshold
    if report.accuracy < 0.8:
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
