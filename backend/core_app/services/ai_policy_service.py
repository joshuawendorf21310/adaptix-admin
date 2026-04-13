"""AI policy service for model governance and safety rules."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core_app.models.ai_policy import AIModelConfig, AIPolicyRule, AIPolicyRuleType, AIPolicyStatus, AIPolicyViolation


class AIPolicyService:
    """Service for managing AI policies and model governance."""

    def __init__(self) -> None:
        self._rules_path = Path(__file__).resolve().parents[2] / "data" / "ai_policy_rules.json"
        self._violations_path = Path(__file__).resolve().parents[2] / "data" / "ai_violations.json"
        self._models_path = Path(__file__).resolve().parents[2] / "data" / "ai_models.json"

        for path in [self._rules_path, self._violations_path, self._models_path]:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("[]", encoding="utf-8")

    def list_rules(
        self,
        rule_type: AIPolicyRuleType | None = None,
        status: AIPolicyStatus | None = None,
    ) -> list[dict[str, Any]]:
        """List AI policy rules."""
        rules = self._read_rules()
        if rule_type:
            rules = [r for r in rules if r["rule_type"] == rule_type.value]
        if status:
            rules = [r for r in rules if r["status"] == status.value]
        return rules

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Get a single AI policy rule."""
        rules = self._read_rules()
        return next((r for r in rules if r["id"] == rule_id), None)

    def create_rule(
        self,
        name: str,
        rule_type: AIPolicyRuleType,
        created_by: str,
        description: str = "",
        config: dict[str, Any] | None = None,
        conditions: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
        status: AIPolicyStatus = AIPolicyStatus.DRAFT,
    ) -> dict[str, Any]:
        """Create a new AI policy rule."""
        rules = self._read_rules()
        now = datetime.now(UTC)
        rule = {
            "id": str(uuid4()),
            "name": name,
            "rule_type": rule_type.value,
            "status": status.value,
            "description": description,
            "config": config or {},
            "conditions": conditions or {},
            "actions": actions or {},
            "version": 1,
            "previous_version_id": None,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "updated_at": now.isoformat(),
            "updated_by": created_by,
            "last_simulated_at": None,
        }
        rules.append(rule)
        self._write_rules(rules)
        return rule

    def update_rule(self, rule_id: str, updated_by: str, **updates: Any) -> dict[str, Any] | None:
        """Update an AI policy rule."""
        rules = self._read_rules()
        for rule in rules:
            if rule["id"] == rule_id:
                # Create new version
                old_version = rule.copy()
                rule.update({k: v for k, v in updates.items() if v is not None})
                rule["updated_at"] = datetime.now(UTC).isoformat()
                rule["updated_by"] = updated_by
                rule["version"] = rule.get("version", 1) + 1
                rule["previous_version_id"] = old_version["id"]
                self._write_rules(rules)
                return rule
        return None

    def delete_rule(self, rule_id: str) -> bool:
        """Delete an AI policy rule."""
        rules = self._read_rules()
        new_rules = [r for r in rules if r["id"] != rule_id]
        if len(new_rules) == len(rules):
            return False
        self._write_rules(new_rules)
        return True

    def simulate_rule(self, rule_id: str) -> dict[str, Any]:
        """Simulate an AI policy rule (dry-run mode)."""
        rule = self.get_rule(rule_id)
        if not rule:
            return {"error": "Rule not found"}

        rules = self._read_rules()
        for r in rules:
            if r["id"] == rule_id:
                r["last_simulated_at"] = datetime.now(UTC).isoformat()
                self._write_rules(rules)
                break

        return {
            "rule_id": rule_id,
            "simulated_at": datetime.now(UTC).isoformat(),
            "status": "simulation_complete",
            "message": "Simulation mode: no actual enforcement applied",
        }

    def activate_rule(self, rule_id: str, activated_by: str) -> dict[str, Any] | None:
        """Activate an AI policy rule for enforcement."""
        return self.update_rule(rule_id, activated_by, status=AIPolicyStatus.ACTIVE.value)

    def deactivate_rule(self, rule_id: str, deactivated_by: str) -> dict[str, Any] | None:
        """Deactivate an AI policy rule."""
        return self.update_rule(rule_id, deactivated_by, status=AIPolicyStatus.DISABLED.value)

    # AI model management
    def list_models(self, allowed_only: bool = False) -> list[dict[str, Any]]:
        """List AI model configurations."""
        models = self._read_models()
        if allowed_only:
            models = [m for m in models if m.get("allowed", False)]
        return models

    def add_model(
        self,
        model_id: str,
        model_name: str,
        provider: str,
        allowed: bool = True,
        requires_human_review: bool = False,
        redaction_required: bool = False,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add an AI model to the allowlist/denylist."""
        models = self._read_models()
        model = {
            "model_id": model_id,
            "model_name": model_name,
            "provider": provider,
            "allowed": allowed,
            "requires_human_review": requires_human_review,
            "max_tokens": None,
            "temperature_limit": None,
            "redaction_required": redaction_required,
            "retention_days": None,
            "tags": tags or [],
        }
        models.append(model)
        self._write_models(models)
        return model

    def update_model(self, model_id: str, **updates: Any) -> dict[str, Any] | None:
        """Update an AI model configuration."""
        models = self._read_models()
        for model in models:
            if model["model_id"] == model_id:
                model.update({k: v for k, v in updates.items() if v is not None})
                self._write_models(models)
                return model
        return None

    # Violation tracking
    def record_violation(
        self,
        policy_rule_id: str,
        policy_rule_name: str,
        violation_type: str,
        tenant_id: str,
        user_id: str,
        severity: str = "warning",
        model_used: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an AI policy violation."""
        violations = self._read_violations()
        violation = {
            "id": str(uuid4()),
            "policy_rule_id": policy_rule_id,
            "policy_rule_name": policy_rule_name,
            "violation_type": violation_type,
            "severity": severity,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "model_used": model_used,
            "prompt_hash": None,
            "output_hash": None,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details or {},
            "remediated": False,
            "remediated_by": None,
            "remediated_at": None,
        }
        violations.append(violation)
        self._write_violations(violations)
        return violation

    def list_violations(
        self,
        tenant_id: str | None = None,
        severity: str | None = None,
        remediated: bool | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List AI policy violations."""
        violations = self._read_violations()
        if tenant_id:
            violations = [v for v in violations if v["tenant_id"] == tenant_id]
        if severity:
            violations = [v for v in violations if v["severity"] == severity]
        if remediated is not None:
            violations = [v for v in violations if v["remediated"] == remediated]
        return violations[-limit:]

    def remediate_violation(self, violation_id: str, remediated_by: str) -> dict[str, Any] | None:
        """Mark a violation as remediated."""
        violations = self._read_violations()
        for violation in violations:
            if violation["id"] == violation_id:
                violation["remediated"] = True
                violation["remediated_by"] = remediated_by
                violation["remediated_at"] = datetime.now(UTC).isoformat()
                self._write_violations(violations)
                return violation
        return None

    def _read_rules(self) -> list[dict[str, Any]]:
        return json.loads(self._rules_path.read_text(encoding="utf-8"))

    def _write_rules(self, rules: list[dict[str, Any]]) -> None:
        self._rules_path.write_text(json.dumps(rules, indent=2), encoding="utf-8")

    def _read_violations(self) -> list[dict[str, Any]]:
        return json.loads(self._violations_path.read_text(encoding="utf-8"))

    def _write_violations(self, violations: list[dict[str, Any]]) -> None:
        self._violations_path.write_text(json.dumps(violations, indent=2), encoding="utf-8")

    def _read_models(self) -> list[dict[str, Any]]:
        return json.loads(self._models_path.read_text(encoding="utf-8"))

    def _write_models(self, models: list[dict[str, Any]]) -> None:
        self._models_path.write_text(json.dumps(models, indent=2), encoding="utf-8")


ai_policy_service = AIPolicyService()
