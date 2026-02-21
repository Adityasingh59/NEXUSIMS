"""NEXUS IMS — Workflow Execution Celery Tasks (Block 9)."""
import json
import logging

from app.db.session import async_session_factory
from app.models.workflow import ActionType, WorkflowAction, WorkflowExecution, ExecutionStatus
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_workflow(self, workflow_id: str, payload: dict) -> list[dict]:
    """
    Executes a workflow by running all its actions sequentially.
    Runs asynchronously and logs the result into WorkflowExecution.
    """
    import asyncio
    return asyncio.run(_execute_workflow_async(workflow_id, payload))


async def _execute_workflow_async(workflow_id: str, payload: dict) -> list[dict]:
    async with async_session_factory() as db:
        from sqlalchemy import select

        # Create Execution Record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            trigger_event_id=payload.get("event_id"),
            status=ExecutionStatus.RUNNING.value,
            trigger_payload=payload,
        )
        db.add(execution)
        await db.commit()

        # Fetch Actions
        stmt = select(WorkflowAction).where(WorkflowAction.workflow_id == workflow_id).order_by(WorkflowAction.sequence_order)
        result = await db.execute(stmt)
        actions = result.scalars().all()

        results = []
        has_failure = False

        for action in actions:
            action_result = {
                "action_id": str(action.id),
                "type": action.action_type,
                "status": "SUCCESS",
                "error": None
            }
            try:
                # Dispatch to specific action handlers
                if action.action_type == ActionType.PRINT_LABEL:
                    await _handle_print_label(action.action_config, payload)
                elif action.action_type == ActionType.SEND_EMAIL:
                    await _handle_send_email(action.action_config, payload)
                elif action.action_type == ActionType.WEBHOOK:
                    await _handle_webhook(action.action_config, payload)
                elif action.action_type == ActionType.FLAG_FOR_REVIEW:
                    await _handle_flag_review(action.action_config, payload, db)
                elif action.action_type == ActionType.NOTIFY_USER:
                    await _handle_notify_user(action.action_config, payload, db)
                else:
                    raise ValueError(f"Unknown action type: {action.action_type}")

            except Exception as e:
                logger.error(f"Action {action.action_type} failed: {e}")
                action_result["status"] = "FAILED"
                action_result["error"] = str(e)
                has_failure = True
                # Decide if we stop on first failure or continue. Block 9 spec implies stop sequence.
                results.append(action_result)
                break
            
            results.append(action_result)

        # Update Execution Record
        execution.status = ExecutionStatus.FAILED.value if has_failure else ExecutionStatus.SUCCESS.value
        execution.actions_results = results
        from datetime import datetime, timezone
        execution.completed_at = datetime.now(tz=timezone.utc)
        
        await db.commit()
        return results


# --- Action Handlers (Stubs/Simulations for Phase 2 MVP) ---

async def _handle_print_label(config: dict, payload: dict):
    printers = config.get("printer_ip", "0.0.0.0")
    logger.info(f"[ZPL PRINT SIMULATION] Sending ZPL to {printers} for SKU {payload.get('sku')}...")


async def _handle_send_email(config: dict, payload: dict):
    to_email = config.get("to")
    subject = config.get("subject", "NEXUS Alert")
    logger.info(f"[EMAIL SIMULATION] Sending via SendGrid to {to_email}: {subject}")


async def _handle_webhook(config: dict, payload: dict):
    """If workflow natively triggers a webhook via action (independent of global webhooks)"""
    url = config.get("url")
    logger.info(f"[WEBHOOK SIMULATION] POSTing to {url}")
    # Integration with webhook delivery system could happen here, or simple requests.post


async def _handle_flag_review(config: dict, payload: dict, db):
    # E.g. Insert an alert into a dashboard_alerts table.
    logger.info(f"[FLAG REVIEW] Flagging {payload} for review.")


async def _handle_notify_user(config: dict, payload: dict, db):
    logger.info(f"[NOTIFY USER] In-app notification to role {config.get('role')}")
