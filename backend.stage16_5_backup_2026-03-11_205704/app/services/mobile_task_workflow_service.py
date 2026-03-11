from __future__ import annotations

from sqlalchemy import text
from app.db import SessionLocal


def _payload_json(kind: str, actor_user_id: str, comment: str | None = None) -> str:
    if comment is None:
        comment_json = "null"
    else:
        comment_json = '"' + comment.replace('"', '\\"') + '"'
    return (
        '{'
        f'"kind":"{kind}",'
        f'"actor_user_id":"{actor_user_id}",'
        f'"comment":{comment_json}'
        '}'
    )


async def _assert_manager_access(session, task_id: str, actor_user_id: str, actor_role: str) -> None:
    if actor_role == "dispatcher":
        return

    row = (
        await session.execute(
            text(
                """
                select 1
                from tasks t
                join stores s on s.id = t.store_id
                where t.id = :task_id
                  and s.assigned_user_id::text = :actor_user_id
                """
            ),
            {"task_id": task_id, "actor_user_id": actor_user_id},
        )
    ).first()

    if not row:
        raise PermissionError("Task is not assigned to this manager")


async def get_task_detail(task_id: str, actor_user_id: str, actor_role: str):
    async with SessionLocal() as session:
        await _assert_manager_access(session, task_id, actor_user_id, actor_role)

        task_row = (
            await session.execute(
                text(
                    """
                    select
                        t.id,
                        t.portal_task_id,
                        t.status,
                        coalesce(t.sla, t.sla_due_at) as sla,
                        t.last_seen_at,
                        t.payload,
                        s.store_no,
                        coalesce(u.full_name, u.email, '—') as manager_name,
                        tis.internal_status,
                        tis.accepted_at,
                        tis.accepted_by,
                        tis.closed_at,
                        tis.closed_by,
                        tis.manager_comment
                    from tasks t
                    left join stores s on s.id = t.store_id
                    left join users u on u.id = s.assigned_user_id
                    left join task_internal_state tis on tis.task_id = t.id
                    where t.id = :task_id
                    """
                ),
                {"task_id": task_id},
            )
        ).mappings().first()

        if not task_row:
            raise ValueError("Task not found")

        comments = (
            await session.execute(
                text(
                    """
                    select
                        c.id,
                        c.comment_text,
                        c.created_at,
                        coalesce(u.full_name, u.email, c.created_by::text, '—') as author_name
                    from task_comments c
                    left join users u on u.id = c.created_by
                    where c.task_id = :task_id
                    order by c.created_at desc
                    """
                ),
                {"task_id": task_id},
            )
        ).mappings().all()

        return {
            "task": dict(task_row),
            "comments": [dict(x) for x in comments],
        }


async def accept_task(task_id: str, actor_user_id: str, actor_role: str):
    async with SessionLocal() as session:
        await _assert_manager_access(session, task_id, actor_user_id, actor_role)

        await session.execute(
            text(
                """
                insert into task_internal_state (task_id, internal_status, accepted_at, accepted_by)
                values (:task_id, 'accepted', now(), :actor_user_id::uuid)
                on conflict (task_id) do update
                set internal_status = 'accepted',
                    accepted_at = now(),
                    accepted_by = :actor_user_id::uuid
                """
            ),
            {"task_id": task_id, "actor_user_id": actor_user_id},
        )

        await session.execute(
            text(
                """
                insert into task_events (id, task_id, event_type, payload, created_at)
                values (gen_random_uuid(), :task_id, 'manager_accept', cast(:payload as jsonb), now())
                """
            ),
            {"task_id": task_id, "payload": _payload_json("manager_accept", actor_user_id)},
        )

        await session.commit()
        return {"accepted": True, "task_id": task_id}


async def add_comment(task_id: str, comment: str, actor_user_id: str, actor_role: str):
    async with SessionLocal() as session:
        await _assert_manager_access(session, task_id, actor_user_id, actor_role)

        await session.execute(
            text(
                """
                insert into task_comments (id, task_id, created_by, comment_text, created_at)
                values (gen_random_uuid(), :task_id, :actor_user_id::uuid, :comment, now())
                """
            ),
            {"task_id": task_id, "actor_user_id": actor_user_id, "comment": comment},
        )

        await session.execute(
            text(
                """
                insert into task_events (id, task_id, event_type, payload, created_at)
                values (gen_random_uuid(), :task_id, 'manager_comment', cast(:payload as jsonb), now())
                """
            ),
            {"task_id": task_id, "payload": _payload_json("manager_comment", actor_user_id, comment)},
        )

        await session.commit()
        return {"comment_added": True, "task_id": task_id}


async def close_task(task_id: str, comment: str | None, actor_user_id: str, actor_role: str):
    async with SessionLocal() as session:
        await _assert_manager_access(session, task_id, actor_user_id, actor_role)

        await session.execute(
            text(
                """
                insert into task_internal_state
                    (task_id, internal_status, closed_at, closed_by, manager_comment)
                values
                    (:task_id, 'closed', now(), :actor_user_id::uuid, :comment)
                on conflict (task_id) do update
                set internal_status = 'closed',
                    closed_at = now(),
                    closed_by = :actor_user_id::uuid,
                    manager_comment = coalesce(:comment, task_internal_state.manager_comment)
                """
            ),
            {"task_id": task_id, "actor_user_id": actor_user_id, "comment": comment},
        )

        await session.execute(
            text(
                """
                insert into task_events (id, task_id, event_type, payload, created_at)
                values (gen_random_uuid(), :task_id, 'manager_close', cast(:payload as jsonb), now())
                """
            ),
            {"task_id": task_id, "payload": _payload_json("manager_close", actor_user_id, comment)},
        )

        await session.commit()
        return {"closed": True, "task_id": task_id}
