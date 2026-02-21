"""NEXUS IMS — Workflow Engine (Block 9)."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow


class ConditionEvaluator:
    """Evaluates JSONB trigger conditions against a payload."""

    @staticmethod
    def evaluate(conditions: dict, payload: dict) -> bool:
        """
        Evaluate conditions against a payload.
        Conditions format:
        {
            "operator": "AND" | "OR",
            "conditions": [
                {"field": "quantity", "operator": "greater_than", "value": 100},
                {"operator": "OR", "conditions": [...]}
            ]
        }
        """
        if not conditions:
            return True  # No conditions = run always

        op = conditions.get("operator", "AND").upper()
        sub_conditions = conditions.get("conditions", [])

        if not sub_conditions:
            return True

        if op == "AND":
            return all(ConditionEvaluator._eval_single(c, payload) for c in sub_conditions)
        elif op == "OR":
            return any(ConditionEvaluator._eval_single(c, payload) for c in sub_conditions)
        return False

    @staticmethod
    def _eval_single(condition: dict, payload: dict) -> bool:
        if "operator" in condition and "conditions" in condition:
            return ConditionEvaluator.evaluate(condition, payload)

        field = condition.get("field")
        operator = condition.get("operator")
        expected_value = condition.get("value")

        if not field or not operator:
            return False

        # Nested generic get
        actual_value = payload
        for part in field.split("."):
            if isinstance(actual_value, dict):
                actual_value = actual_value.get(part)
            else:
                actual_value = None
                break

        if actual_value is None and operator != "not_equals":
            return False

        try:
            if operator == "equals":
                return actual_value == expected_value
            elif operator == "not_equals":
                return actual_value != expected_value
            elif operator == "greater_than":
                return float(actual_value) > float(expected_value)
            elif operator == "less_than":
                return float(actual_value) < float(expected_value)
            elif operator == "contains":
                return str(expected_value).lower() in str(actual_value).lower()
            else:
                return False
        except (ValueError, TypeError):
            return False


class WorkflowEngine:
    """Core engine for evaluating and triggering workflows."""

    @staticmethod
    async def evaluate(db: AsyncSession, tenant_id: str, trigger_type: str, payload: dict) -> list[str]:
        """
        Evaluate active workflows for a tenant and trigger, dispatching if conditions pass.
        Returns a list of workflow lengths that were dispatched.
        """
        # Get active workflows matching tenant and trigger type
        stmt = select(Workflow).where(
            Workflow.tenant_id == tenant_id,
            Workflow.trigger_type == trigger_type,
            Workflow.is_active == True,
        )
        result = await db.execute(stmt)
        workflows = result.scalars().all()

        dispatched_workflow_ids = []

        from app.tasks.workflow_tasks import execute_workflow

        for workflow in workflows:
            passed = ConditionEvaluator.evaluate(workflow.trigger_config, payload)
            if passed:
                # Dispatch celery task
                execute_workflow.delay(str(workflow.id), payload)
                dispatched_workflow_ids.append(str(workflow.id))

        return dispatched_workflow_ids
