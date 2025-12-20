"""Multi-LLM Orchestration for consensus-based analysis with iterative discussion."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import litellm

from config.settings import Settings, get_settings


@dataclass
class LLMResponse:
    """Response from a single LLM."""
    model: str
    content: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    round_number: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "round_number": self.round_number,
        }


@dataclass
class EvaluationScore:
    """Evaluation score from one LLM about another's response."""
    evaluator_model: str
    target_model: str
    score: float  # 0-10
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "evaluator_model": self.evaluator_model,
            "target_model": self.target_model,
            "score": self.score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
        }


@dataclass
class DiscussionRound:
    """A single round of discussion in the consensus process."""
    round_number: int
    responses: List[LLMResponse]
    evaluations: List[EvaluationScore]
    consensus_score: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "round_number": self.round_number,
            "responses": [r.to_dict() for r in self.responses],
            "evaluations": [e.to_dict() for e in self.evaluations],
            "consensus_score": self.consensus_score,
            "timestamp": self.timestamp,
        }


@dataclass 
class ConsensusResult:
    """Result of multi-LLM consensus with full discussion history."""
    consensus_content: str
    agreement_score: float
    individual_responses: List[LLMResponse]
    disagreements: List[str] = field(default_factory=list)
    discussion_rounds: List[DiscussionRound] = field(default_factory=list)
    final_evaluations: Dict[str, float] = field(default_factory=dict)  # model -> avg score
    referenced_sessions: List[str] = field(default_factory=list)
    referenced_clusters: List[int] = field(default_factory=list)
    agreement_points: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "consensus_content": self.consensus_content,
            "agreement_score": self.agreement_score,
            "individual_responses": [r.to_dict() for r in self.individual_responses],
            "disagreements": self.disagreements,
            "discussion_rounds": [r.to_dict() for r in self.discussion_rounds],
            "final_evaluations": self.final_evaluations,
            "referenced_sessions": self.referenced_sessions,
            "referenced_clusters": self.referenced_clusters,
            "agreement_points": self.agreement_points,
        }


CONSENSUS_PROMPT = """以下は複数のAIモデルによる同じ質問への回答です。
これらの回答を統合し、合意点を抽出してください。

## 各モデルの回答
{responses}

## 指示
1. 全てのモデルが同意している点を抽出してください
2. 意見が分かれている点があれば記載してください
3. 統合した最終回答を作成してください
4. 参照されているセッションIDがあれば抽出してください

JSON形式で出力してください：
{{
    "consensus": "統合された回答",
    "agreement_points": ["合意点1", "合意点2", ...],
    "disagreement_points": ["意見が分かれた点1", ...],
    "referenced_sessions": ["session_id1", "session_id2", ...],
    "referenced_clusters": [1, 2, 3, ...]
}}
"""


EVALUATION_PROMPT = """あなたは法案分析レポートの品質を評価する専門家です。
以下の分析レポートを評価してください。

## 評価対象のレポート
{target_response}

## 評価基準
1. **インサイトの質** (0-10): 法案検討に参考になる具体的な知見が含まれているか
2. **正確性** (0-10): 元データを正確に反映しているか
3. **構成・読みやすさ** (0-10): 論理的で読みやすい構成か
4. **バランス** (0-10): 賛成・反対の意見をバランスよく取り上げているか

JSON形式で評価を出力してください：
{{
    "total_score": 0-10の総合スコア,
    "strengths": ["強み1", "強み2", ...],
    "weaknesses": ["改善点1", "改善点2", ...],
    "suggestions": ["具体的な改善提案1", ...]
}}
"""


ITERATIVE_PROMPT = """前回のラウンドで他のAIモデルから以下のフィードバックを受けました。
このフィードバックを踏まえて、分析を改善してください。

## 前回のあなたの回答
{previous_response}

## 他モデルからのフィードバック
{feedback}

## 元の分析タスク
{original_prompt}

フィードバックを踏まえて改善した分析を提供してください。
特に以下の点に注意してください：
- 指摘された弱点を改善する
- 提案された改善点を取り入れる
- 参照するセッションID・クラスタを明示する
"""


class MultiLLMOrchestrator:
    """Orchestrate multiple LLMs for consensus-based analysis with iterative discussion."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        models: Optional[List[str]] = None,
        max_rounds: int = 3,
        consensus_threshold: float = 0.8,
    ):
        """Initialize multi-LLM orchestrator.
        
        Args:
            settings: Application settings
            models: List of model identifiers to use
            max_rounds: Maximum discussion rounds (default: 3)
            consensus_threshold: Agreement score threshold to stop (default: 0.8)
        """
        self.settings = settings or get_settings()
        self.models = models or self.settings.multi_llm_models
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        
        # Ensure we have at least one model
        if not self.models:
            raise ValueError("At least one model must be specified")
    
    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Call a single model.
        
        Args:
            model: Model identifier
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLMResponse object
        """
        import time
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        # Add openrouter/ prefix if not present and using OpenRouter
        model_name = model
        if not model.startswith("openrouter/") and self.settings.openrouter_api_key:
            model_name = f"openrouter/{model}"
        
        try:
            # Build kwargs for litellm
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            }
            
            # Add OpenRouter API key and base URL if available
            if self.settings.openrouter_api_key:
                kwargs["api_key"] = self.settings.openrouter_api_key
                kwargs["api_base"] = self.settings.openrouter_base_url
            
            response = await litellm.acompletion(**kwargs)
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            latency = (time.time() - start_time) * 1000
            
            return LLMResponse(
                model=model,
                content=content,
                tokens_used=tokens,
                latency_ms=latency,
            )
        except Exception as e:
            return LLMResponse(
                model=model,
                content=f"Error: {str(e)}",
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def gather_responses(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        """Gather responses from all models in parallel.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            List of LLMResponse objects
        """
        tasks = [
            self._call_model(model, prompt, system_prompt)
            for model in self.models
        ]
        
        responses = await asyncio.gather(*tasks)
        return list(responses)
    
    async def _evaluate_response(
        self,
        evaluator_model: str,
        target_response: LLMResponse,
    ) -> EvaluationScore:
        """Have one model evaluate another's response.
        
        Args:
            evaluator_model: Model doing the evaluation
            target_response: Response being evaluated
            
        Returns:
            EvaluationScore object
        """
        eval_prompt = EVALUATION_PROMPT.format(
            target_response=target_response.content
        )
        
        response = await self._call_model(
            evaluator_model,
            eval_prompt,
            system_prompt="あなたは法案分析レポートの品質評価の専門家です。客観的かつ建設的なフィードバックを提供してください。"
        )
        
        try:
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response.content[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            return EvaluationScore(
                evaluator_model=evaluator_model,
                target_model=target_response.model,
                score=float(data.get("total_score", 5)),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                suggestions=data.get("suggestions", []),
            )
        except Exception:
            return EvaluationScore(
                evaluator_model=evaluator_model,
                target_model=target_response.model,
                score=5.0,
                strengths=["評価の解析に失敗"],
                weaknesses=[],
                suggestions=[],
            )
    
    async def _evaluate_all_responses(
        self,
        responses: List[LLMResponse],
    ) -> List[EvaluationScore]:
        """Have each model evaluate all other models' responses.
        
        Args:
            responses: List of responses to evaluate
            
        Returns:
            List of EvaluationScore objects
        """
        valid_responses = [r for r in responses if not r.content.startswith("Error:")]
        
        tasks = []
        for evaluator_resp in valid_responses:
            for target_resp in valid_responses:
                if evaluator_resp.model != target_resp.model:
                    tasks.append(
                        self._evaluate_response(evaluator_resp.model, target_resp)
                    )
        
        if not tasks:
            return []
        
        evaluations = await asyncio.gather(*tasks)
        return list(evaluations)
    
    def _calculate_consensus_score(
        self,
        evaluations: List[EvaluationScore],
    ) -> float:
        """Calculate overall consensus score from evaluations.
        
        Args:
            evaluations: List of evaluation scores
            
        Returns:
            Consensus score (0-1)
        """
        if not evaluations:
            return 0.5
        
        avg_score = sum(e.score for e in evaluations) / len(evaluations)
        # Normalize to 0-1 range (from 0-10)
        return avg_score / 10.0
    
    def _get_feedback_for_model(
        self,
        model: str,
        evaluations: List[EvaluationScore],
    ) -> str:
        """Get aggregated feedback for a specific model.
        
        Args:
            model: Model to get feedback for
            evaluations: All evaluations
            
        Returns:
            Formatted feedback string
        """
        model_evals = [e for e in evaluations if e.target_model == model]
        
        if not model_evals:
            return "フィードバックなし"
        
        feedback_parts = []
        for eval in model_evals:
            parts = [f"### {eval.evaluator_model}からの評価 (スコア: {eval.score}/10)"]
            
            if eval.strengths:
                parts.append("**強み:**")
                parts.extend([f"- {s}" for s in eval.strengths])
            
            if eval.weaknesses:
                parts.append("**改善点:**")
                parts.extend([f"- {w}" for w in eval.weaknesses])
            
            if eval.suggestions:
                parts.append("**提案:**")
                parts.extend([f"- {s}" for s in eval.suggestions])
            
            feedback_parts.append("\n".join(parts))
        
        return "\n\n".join(feedback_parts)
    
    async def reach_consensus_iterative(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Reach consensus through iterative discussion rounds.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            consensus_model: Model to use for final consensus
            
        Returns:
            ConsensusResult with full discussion history
        """
        discussion_rounds: List[DiscussionRound] = []
        current_responses: List[LLMResponse] = []
        original_prompt = prompt
        
        for round_num in range(1, self.max_rounds + 1):
            # Round 1: Initial responses
            if round_num == 1:
                current_responses = await self.gather_responses(prompt, system_prompt)
            else:
                # Subsequent rounds: Improve based on feedback
                prev_round = discussion_rounds[-1]
                improved_tasks = []
                
                # #region agent log
                import json as _json; open('/Users/masa/forback/github/mirai_DB_backup/.cursor/debug.log', 'a').write(_json.dumps({"location":"multi_llm.py:448","message":"Processing responses for improvement","data":{"round_num":round_num,"num_responses":len(current_responses),"error_responses":[r.model for r in current_responses if r.content.startswith("Error:")]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","hypothesisId":"A"})+'\n')
                # #endregion
                
                async def _return_existing_response(r):
                    """Helper to return existing response as a coroutine for asyncio.gather compatibility."""
                    return r
                
                for resp in current_responses:
                    if resp.content.startswith("Error:"):
                        # #region agent log
                        import json as _json; open('/Users/masa/forback/github/mirai_DB_backup/.cursor/debug.log', 'a').write(_json.dumps({"location":"multi_llm.py:450","message":"Skipping error response","data":{"model":resp.model,"error_prefix":resp.content[:100]},"timestamp":__import__('time').time()*1000,"sessionId":"debug-session","hypothesisId":"A"})+'\n')
                        # #endregion
                        improved_tasks.append(_return_existing_response(resp))
                        continue
                    
                    feedback = self._get_feedback_for_model(resp.model, prev_round.evaluations)
                    improve_prompt = ITERATIVE_PROMPT.format(
                        previous_response=resp.content,
                        feedback=feedback,
                        original_prompt=original_prompt,
                    )
                    improved_tasks.append(
                        self._call_model(resp.model, improve_prompt, system_prompt)
                    )
                
                current_responses = await asyncio.gather(*improved_tasks)
                current_responses = list(current_responses)
            
            # Set round number for all responses
            for resp in current_responses:
                resp.round_number = round_num
            
            # Evaluate all responses
            evaluations = await self._evaluate_all_responses(current_responses)
            
            # Calculate consensus score
            consensus_score = self._calculate_consensus_score(evaluations)
            
            # Create discussion round record
            discussion_round = DiscussionRound(
                round_number=round_num,
                responses=current_responses.copy(),
                evaluations=evaluations,
                consensus_score=consensus_score,
            )
            discussion_rounds.append(discussion_round)
            
            # Check if consensus reached
            if consensus_score >= self.consensus_threshold:
                break
        
        # Final consensus synthesis
        valid_responses = [r for r in current_responses if not r.content.startswith("Error:")]
        
        if not valid_responses:
            return ConsensusResult(
                consensus_content="All models failed to respond",
                agreement_score=0.0,
                individual_responses=current_responses,
                disagreements=["No valid responses received"],
                discussion_rounds=discussion_rounds,
            )
        
        # Use first model for final synthesis if not specified
        consensus_model = consensus_model or self.models[0]
        
        responses_text = "\n\n".join(
            f"### {r.model}\n{r.content}"
            for r in valid_responses
        )
        
        final_prompt = CONSENSUS_PROMPT.format(responses=responses_text)
        consensus_response = await self._call_model(consensus_model, final_prompt)
        
        # Calculate final evaluations (average score per model)
        final_evaluations = {}
        last_round_evals = discussion_rounds[-1].evaluations if discussion_rounds else []
        for model in self.models:
            model_scores = [e.score for e in last_round_evals if e.target_model == model]
            if model_scores:
                final_evaluations[model] = sum(model_scores) / len(model_scores)
        
        # Parse consensus response
        try:
            json_start = consensus_response.content.find('{')
            json_end = consensus_response.content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(consensus_response.content[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            num_agreements = len(data.get("agreement_points", []))
            num_disagreements = len(data.get("disagreement_points", []))
            total = num_agreements + num_disagreements
            agreement_score = num_agreements / total if total > 0 else discussion_rounds[-1].consensus_score
            
            return ConsensusResult(
                consensus_content=data.get("consensus", ""),
                agreement_score=agreement_score,
                individual_responses=current_responses,
                disagreements=data.get("disagreement_points", []),
                discussion_rounds=discussion_rounds,
                final_evaluations=final_evaluations,
                referenced_sessions=data.get("referenced_sessions", []),
                referenced_clusters=data.get("referenced_clusters", []),
                agreement_points=data.get("agreement_points", []),
            )
        except Exception:
            return ConsensusResult(
                consensus_content=valid_responses[0].content,
                agreement_score=discussion_rounds[-1].consensus_score if discussion_rounds else 0.5,
                individual_responses=current_responses,
                disagreements=["Failed to parse consensus response"],
                discussion_rounds=discussion_rounds,
                final_evaluations=final_evaluations,
            )
    
    async def reach_consensus(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Gather responses and reach consensus (single round, legacy method).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            consensus_model: Model to use for consensus
            
        Returns:
            ConsensusResult object
        """
        # Use iterative method with max_rounds=1 for backward compatibility
        original_max_rounds = self.max_rounds
        self.max_rounds = 1
        result = await self.reach_consensus_iterative(prompt, system_prompt, consensus_model)
        self.max_rounds = original_max_rounds
        return result
    
    def gather_responses_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        """Synchronous wrapper for gather_responses."""
        return asyncio.run(self.gather_responses(prompt, system_prompt))
    
    def reach_consensus_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Synchronous wrapper for reach_consensus."""
        return asyncio.run(self.reach_consensus(prompt, system_prompt, consensus_model))
    
    def reach_consensus_iterative_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Synchronous wrapper for reach_consensus_iterative."""
        return asyncio.run(self.reach_consensus_iterative(prompt, system_prompt, consensus_model))


def save_multi_llm_outputs(
    result: ConsensusResult,
    output_dir: Path,
    survey_title: str = "",
) -> Dict[str, Path]:
    """Save all multi-LLM outputs to files.
    
    Args:
        result: ConsensusResult with discussion history
        output_dir: Base output directory
        survey_title: Survey title for headers
        
    Returns:
        Dictionary of output file paths
    """
    multi_llm_dir = output_dir / "multi_llm"
    multi_llm_dir.mkdir(parents=True, exist_ok=True)
    
    output_files = {}
    
    # 1. Save individual model outputs (final round)
    for response in result.individual_responses:
        if response.content.startswith("Error:"):
            continue
        
        # Sanitize model name for filename
        model_name = response.model.replace("/", "_").replace(".", "_")
        filename = f"{model_name}_output.md"
        filepath = multi_llm_dir / filename
        
        content = f"""# {survey_title} - {response.model} 分析結果

**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**ラウンド**: {response.round_number}
**トークン数**: {response.tokens_used}
**レイテンシ**: {response.latency_ms:.0f}ms

---

{response.content}
"""
        filepath.write_text(content, encoding='utf-8')
        output_files[response.model] = filepath
    
    # 2. Save discussion log
    discussion_log_path = multi_llm_dir / "discussion_log.md"
    discussion_content = [f"# {survey_title} - Multi-LLM 議論ログ\n"]
    discussion_content.append(f"**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    discussion_content.append(f"**参加モデル**: {', '.join(result.final_evaluations.keys())}")
    discussion_content.append(f"**最終合意スコア**: {result.agreement_score:.1%}\n")
    discussion_content.append("---\n")
    
    for round_data in result.discussion_rounds:
        discussion_content.append(f"## ラウンド {round_data.round_number}")
        discussion_content.append(f"**タイムスタンプ**: {round_data.timestamp}")
        discussion_content.append(f"**合意スコア**: {round_data.consensus_score:.1%}\n")
        
        # Responses in this round
        discussion_content.append("### 各モデルの回答\n")
        for resp in round_data.responses:
            if resp.content.startswith("Error:"):
                discussion_content.append(f"#### {resp.model}\n**エラー**: {resp.content}\n")
            else:
                # Truncate for readability
                truncated = resp.content[:1000] + "..." if len(resp.content) > 1000 else resp.content
                discussion_content.append(f"#### {resp.model}\n{truncated}\n")
        
        # Evaluations in this round
        if round_data.evaluations:
            discussion_content.append("### 相互評価\n")
            discussion_content.append("| 評価者 | 対象 | スコア |")
            discussion_content.append("|--------|------|--------|")
            for eval in round_data.evaluations:
                discussion_content.append(f"| {eval.evaluator_model} | {eval.target_model} | {eval.score}/10 |")
            
            discussion_content.append("\n#### 詳細フィードバック\n")
            for eval in round_data.evaluations:
                discussion_content.append(f"**{eval.evaluator_model} → {eval.target_model}** (スコア: {eval.score}/10)")
                if eval.strengths:
                    discussion_content.append("- 強み: " + ", ".join(eval.strengths[:3]))
                if eval.weaknesses:
                    discussion_content.append("- 改善点: " + ", ".join(eval.weaknesses[:3]))
                if eval.suggestions:
                    discussion_content.append("- 提案: " + ", ".join(eval.suggestions[:3]))
                discussion_content.append("")
        
        discussion_content.append("---\n")
    
    discussion_log_path.write_text("\n".join(discussion_content), encoding='utf-8')
    output_files["discussion_log"] = discussion_log_path
    
    # 3. Save evaluation matrix as JSON
    evaluation_matrix_path = multi_llm_dir / "evaluation_matrix.json"
    evaluation_data = {
        "final_scores": result.final_evaluations,
        "agreement_score": result.agreement_score,
        "rounds": [
            {
                "round": r.round_number,
                "consensus_score": r.consensus_score,
                "evaluations": [e.to_dict() for e in r.evaluations],
            }
            for r in result.discussion_rounds
        ],
    }
    evaluation_matrix_path.write_text(
        json.dumps(evaluation_data, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    output_files["evaluation_matrix"] = evaluation_matrix_path
    
    # 4. Save consensus report
    consensus_report_path = multi_llm_dir / "consensus_report.md"
    consensus_content = f"""# {survey_title} - Multi-LLM 合意レポート

**生成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
**合意スコア**: {result.agreement_score:.1%}
**議論ラウンド数**: {len(result.discussion_rounds)}

---

## 合意された分析結果

{result.consensus_content}

---

## 合意点

{chr(10).join(f"- {p}" for p in result.agreement_points) if result.agreement_points else "なし"}

## 意見が分かれた点

{chr(10).join(f"- {p}" for p in result.disagreements) if result.disagreements else "なし"}

---

## 参照情報

### 参照セッション
{chr(10).join(f"- [セッション {s}](https://depth-interview-ai.vercel.app/report/{s})" for s in result.referenced_sessions) if result.referenced_sessions else "なし"}

### 参照クラスタ
{chr(10).join(f"- クラスタ {c}" for c in result.referenced_clusters) if result.referenced_clusters else "なし"}

---

## 各モデルの最終評価スコア

| モデル | 平均スコア |
|--------|-----------|
{chr(10).join(f"| {m} | {s:.1f}/10 |" for m, s in result.final_evaluations.items())}

---

## 詳細ログへのリンク

- [議論ログ](discussion_log.md)
- [評価マトリクス](evaluation_matrix.json)
- 各モデル出力:
{chr(10).join(f"  - [{m}]({m.replace('/', '_').replace('.', '_')}_output.md)" for m in result.final_evaluations.keys())}
"""
    consensus_report_path.write_text(consensus_content, encoding='utf-8')
    output_files["consensus_report"] = consensus_report_path
    
    return output_files
