"""TradingAnalyst — IntelligenceBridge-powered trading analysis agent.

Connects the IntelligenceBridge + ColonyConsciousness + Evolution skill learner
to provide market analysis, signal generation, trade explanations, and
pattern learning for the trading stack.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TradeDecision:
    """Represents a trading decision with explanation."""

    def __init__(
        self,
        trade_id: str,
        symbol: str,
        action: str,
        confidence: float,
        reasoning: str,
        strategy: str,
        timestamp: float = 0.0,
    ):
        self.trade_id = trade_id
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.reasoning = reasoning
        self.strategy = strategy
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "strategy": self.strategy,
            "timestamp": self.timestamp,
        }


class TradingAnalyst:
    """IntelligenceBridge-powered trading analysis agent.

    Provides:
    - Market analysis via IntelligenceBridge.ask()
    - Strategy evaluation via IntelligenceBridge.think()
    - Historical context via ColonyConsciousness.search_memories()
    - Pattern learning via SkillLearner
    - Interpretable trade explanations

    Usage:
        analyst = TradingAnalyst(intelligence=ib, consciousness=cs, skill_learner=sl)
        analysis = await analyst.analyze_market("BTC/USDT", "1h")
        signal = await analyst.get_signal("BTC/USDT", strategy="momentum")
        explanation = await analyst.explain_decision(trade_id)
        await analyst.learn_from_trade(trade_result)
    """

    def __init__(
        self,
        intelligence: Any = None,
        consciousness: Any = None,
        skill_learner: Any = None,
    ):
        self._intelligence = intelligence
        self._consciousness = consciousness
        self._skill_learner = skill_learner
        self._decisions: Dict[str, TradeDecision] = {}
        self._trade_count = 0
        self._strategy_stats: Dict[str, Dict[str, int]] = {}

    async def analyze_market(self, symbol: str, timeframe: str = "1h") -> Dict[str, Any]:
        """Analyze market conditions for a symbol.

        Uses IntelligenceBridge to query LLM for market analysis.
        """
        if not self._intelligence:
            return {"success": False, "error": "No intelligence bridge wired"}

        prompt = (
            f"Analyze current market conditions for {symbol} on {timeframe} timeframe. "
            f"Provide: trend direction, key support/resistance levels, "
            f"volume analysis, and overall market sentiment."
        )

        try:
            think_fn = self._intelligence.think
            if asyncio.iscoroutinefunction(think_fn):
                result = await think_fn(prompt, temperature=0.3)
            else:
                result = think_fn(prompt, temperature=0.3)

            return {
                "success": result.success,
                "symbol": symbol,
                "timeframe": timeframe,
                "analysis": result.answer,
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_signal(
        self, symbol: str, strategy: str = "momentum"
    ) -> Dict[str, Any]:
        """Generate a trading signal for a symbol using a specific strategy.

        Uses IntelligenceBridge.think() to evaluate strategy conditions.
        """
        if not self._intelligence:
            return {"success": False, "error": "No intelligence bridge wired"}

        # Check if we have a learned skill for this strategy
        learned = None
        if self._skill_learner:
            learned = self._skill_learner.replay(strategy)

        strategy_prompt = self._build_strategy_prompt(symbol, strategy, learned)

        try:
            think_fn = self._intelligence.think
            if asyncio.iscoroutinefunction(think_fn):
                result = await think_fn(strategy_prompt, temperature=0.2)
            else:
                result = think_fn(strategy_prompt, temperature=0.2)

            # Parse signal from result
            signal = self._parse_signal(result.answer, symbol, strategy)

            # Record decision
            self._trade_count += 1
            trade_id = f"trade_{self._trade_count}_{int(time.time())}"
            decision = TradeDecision(
                trade_id=trade_id,
                symbol=symbol,
                action=signal.get("action", "hold"),
                confidence=signal.get("confidence", 0.0),
                reasoning=result.answer,
                strategy=strategy,
            )
            self._decisions[trade_id] = decision

            # Update strategy stats
            if strategy not in self._strategy_stats:
                self._strategy_stats[strategy] = {"calls": 0, "buys": 0, "sells": 0, "holds": 0}
            self._strategy_stats[strategy]["calls"] += 1
            action = signal.get("action", "hold")
            if action in self._strategy_stats[strategy]:
                self._strategy_stats[strategy][action] += 1

            return {
                "success": result.success,
                "trade_id": trade_id,
                "symbol": symbol,
                "strategy": strategy,
                "signal": signal,
                "reasoning": result.answer,
                "provider": result.provider,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def explain_decision(self, trade_id: str) -> str:
        """Provide a human-readable explanation of a trading decision."""
        decision = self._decisions.get(trade_id)
        if not decision:
            return f"Decision {trade_id} not found"

        if not self._intelligence:
            return (
                f"Trade {trade_id}: {decision.action} {decision.symbol} "
                f"({decision.strategy}, confidence={decision.confidence:.2f}). "
                f"Reasoning: {decision.reasoning[:200]}"
            )

        prompt = (
            f"Explain this trading decision in simple terms:\n"
            f"Symbol: {decision.symbol}\n"
            f"Action: {decision.action}\n"
            f"Strategy: {decision.strategy}\n"
            f"Confidence: {decision.confidence:.2f}\n"
            f"Original reasoning: {decision.reasoning[:500]}"
        )

        try:
            think_fn = self._intelligence.think
            if asyncio.iscoroutinefunction(think_fn):
                result = await think_fn(prompt, temperature=0.5)
            else:
                result = think_fn(prompt, temperature=0.5)
            return result.answer
        except Exception as e:
            return f"Error generating explanation: {e}"

    async def learn_from_trade(self, trade_result: Dict[str, Any]) -> None:
        """Record a trade outcome for learning.

        If the trade was successful, record it as a skill pattern.
        """
        if not self._skill_learner:
            return

        trade_id = trade_result.get("trade_id", "")
        success = trade_result.get("success", False)
        pnl = trade_result.get("pnl", 0.0)
        strategy = trade_result.get("strategy", "unknown")

        if success and pnl > 0:
            # Record successful pattern
            self._skill_learner.record_success(
                command=f"trade_{strategy}",
                result=trade_result,
                tags=["trading", strategy],
                context={"pnl": pnl, "trade_id": trade_id},
            )
            logger.info(
                "learned_trade trade_id=%s strategy=%s pnl=%.2f",
                trade_id, strategy, pnl,
            )
        else:
            # Record failure (won't create skill, but tracked)
            self._skill_learner.record_failure(
                command=f"trade_{strategy}",
                result=trade_result,
                tags=["trading", strategy],
            )

    def _build_strategy_prompt(
        self, symbol: str, strategy: str, learned: Optional[Any]
    ) -> str:
        """Build a strategy evaluation prompt."""
        base = f"Generate a {strategy} trading signal for {symbol}."

        if learned:
            base += (
                f"\n\nPreviously learned patterns for {strategy} strategy:\n"
                f"{learned}"
            )

        base += (
            "\n\nProvide: action (buy/sell/hold), entry price, stop loss, "
            "take profit, confidence level (0-1), and brief reasoning."
        )
        return base

    def _parse_signal(self, answer: str, symbol: str, strategy: str) -> Dict[str, Any]:
        """Parse trading signal from LLM response."""
        answer_lower = answer.lower()

        # Determine action
        if "buy" in answer_lower or "long" in answer_lower:
            action = "buy"
        elif "sell" in answer_lower or "short" in answer_lower:
            action = "sell"
        else:
            action = "hold"

        # Estimate confidence from text
        confidence = 0.5
        if "high confidence" in answer_lower or "strong" in answer_lower:
            confidence = 0.8
        elif "low confidence" in answer_lower or "weak" in answer_lower:
            confidence = 0.3
        elif "medium" in answer_lower or "moderate" in answer_lower:
            confidence = 0.6

        return {
            "action": action,
            "confidence": confidence,
            "symbol": symbol,
            "strategy": strategy,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_trades": self._trade_count,
            "active_decisions": len(self._decisions),
            "strategy_stats": self._strategy_stats,
            "intelligence_wired": self._intelligence is not None,
            "consciousness_wired": self._consciousness is not None,
            "skill_learner_wired": self._skill_learner is not None,
        }
