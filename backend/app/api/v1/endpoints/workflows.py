"""NEXUS IMS — Workflows API (Block 9)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.tenant import User
from app.models.workflow import Workflow, WorkflowAction, WorkflowExecution
from app.services.workflow_engine import ConditionEvaluator

router = APIRouter()


@router.get("/")
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all workflows for the tenant."""
    stmt = select(Workflow).options(selectinload(Workflow.actions)).where(
        Workflow.tenant_id == current_user.tenant_id
    ).order_by(Workflow.created_at.desc())
    result = await db.execute(stmt)
    workflows = result.scalars().all()
    
    return {
        "data": workflows,
        "error": None,
        "meta": {"count": len(workflows)}
    }


@router.post("/")
async def create_workflow(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new workflow with actions."""
    name = payload.get("name")
    trigger_type = payload.get("trigger_type")
    trigger_config = payload.get("trigger_config", {})
    actions_payload = payload.get("actions", [])

    if not name or not trigger_type:
        raise HTTPException(status_code=422, detail="name and trigger_type are required")

    workflow = Workflow(
        tenant_id=current_user.tenant_id,
        name=name,
        trigger_type=trigger_type,
        trigger_config=trigger_config,
        is_active=payload.get("is_active", True),
        created_by=current_user.id
    )
    db.add(workflow)
    await db.flush()

    # Add actions
    for idx, act in enumerate(actions_payload):
        action = WorkflowAction(
            workflow_id=workflow.id,
            sequence_order=idx,
            action_type=act.get("action_type"),
            action_config=act.get("action_config", {})
        )
        db.add(action)

    await db.commit()
    await db.refresh(workflow)
    
    # Reload with actions to return
    stmt = select(Workflow).options(selectinload(Workflow.actions)).where(Workflow.id == workflow.id)
    workflow_full = (await db.execute(stmt)).scalar_one()

    return {"data": workflow_full, "error": None, "meta": None}


@router.post("/{workflow_id}/test")
async def test_workflow(
    workflow_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Dry-run test a workflow trigger against a synthetic payload."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow or workflow.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    passed = ConditionEvaluator.evaluate(workflow.trigger_config, payload)
    
    return {
        "data": {
            "workflow_id": workflow_id,
            "conditions_passed": passed,
            "simulated_payload": payload,
            "would_trigger": passed and workflow.is_active
        },
        "error": None,
        "meta": None
    }


@router.get("/{workflow_id}/executions")
async def list_executions(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List execution history for a workflow."""
    workflow = await db.get(Workflow, workflow_id)
    if not workflow or workflow.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    stmt = select(WorkflowExecution).where(
        WorkflowExecution.workflow_id == workflow_id
    ).order_by(WorkflowExecution.started_at.desc()).limit(100)
    result = await db.execute(stmt)
    executions = result.scalars().all()

    return {
        "data": executions,
        "error": None,
        "meta": {"count": len(executions)}
    }
