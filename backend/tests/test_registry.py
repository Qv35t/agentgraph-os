import asyncio
from uuid import uuid4

from agentgraph.runtime.registry import RunRegistry


def test_cancellation_wait_is_bounded() -> None:
    async def run_scenario() -> None:
        registry = RunRegistry()
        release = asyncio.Event()

        async def cancellation_resistant_task() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await release.wait()

        run_id = uuid4()
        task = asyncio.create_task(cancellation_resistant_task())
        registry.register(run_id, task)
        await asyncio.sleep(0)

        assert not await registry.cancel(run_id, timeout_seconds=0.01)
        release.set()
        await task
        registry.remove(run_id)

    asyncio.run(run_scenario())
