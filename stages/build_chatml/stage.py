from yt_framework.core.pipeline import DebugContext
from yt_framework.core.stage import BaseStage
from yt_framework.operations.command_ops.map_reduce import run_map_reduce


class BuildChatMLStage(BaseStage):
    def run(self, debug: DebugContext) -> DebugContext:
        success = run_map_reduce(
            context=self.context,
            operation_config=self.config.client.operations.map_reduce,
            mapper="mapper",
            reducer="reducer",
        )
        if not success:
            raise RuntimeError("Map-reduce operation failed")
        return debug
