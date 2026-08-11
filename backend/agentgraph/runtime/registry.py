import asyncio
from uuid import UUID


class RunRegistry:
    """Tracks only live in-process tasks; durable state remains in SQLite."""

    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    def register(self, run_id: UUID, task: asyncio.Task[None]) -> None:
        self._tasks[run_id] = task

    def get(self, run_id: UUID) -> asyncio.Task[None] | None:
        return self._tasks.get(run_id)

    def remove(self, run_id: UUID) -> None:
        self._tasks.pop(run_id, None)

    async def cancel(self, run_id: UUID, timeout_seconds: float) -> bool:
        task = self.get(run_id)
        if task is None:
            return False
        task.cancel()
        done, _ = await asyncio.wait({task}, timeout=timeout_seconds)
        if done:
            await asyncio.gather(*done, return_exceptions=True)
            return True
        return False

    async def cancel_all(self, timeout_seconds: float) -> tuple[list[UUID], list[UUID]]:
        tasks = list(self._tasks.items())
        for _, task in tasks:
            task.cancel()
        if tasks:
            done, _ = await asyncio.wait({task for _, task in tasks}, timeout=timeout_seconds)
            if done:
                await asyncio.gather(*done, return_exceptions=True)
        completed = [run_id for run_id, task in tasks if task.done()]
        timed_out = [run_id for run_id, task in tasks if not task.done()]
        return completed, timed_out

    async def wait_all(self) -> None:
        tasks = tuple(self._tasks.values())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
