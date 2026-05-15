from yt_framework.core.pipeline import DebugContext
from yt_framework.core.stage import BaseStage
from yt_framework.operations.s3 import list_s3_files
from yt_framework.utils.env import load_secrets
from ytjobs.s3.client import S3Client


class ListS3Stage(BaseStage):
    def __init__(self, deps, logger):
        super().__init__(deps, logger)

        self.s3_client = S3Client.create(
            secrets=load_secrets(self.deps.configs_dir),
            client_type="download",
        )

    def run(self, debug: DebugContext) -> DebugContext:
        paths = list_s3_files(
            s3_client=self.s3_client,
            bucket=self.config.client.input_bucket,
            prefix=self.config.client.input_prefix,
            logger=self.logger,
            extension=self.config.client.file_extension,
            max_files=self.config.client.get("max_files"),
        )
        self.logger.info(f"Found {len(paths)} files")

        if not paths:
            return debug

        rows = [
            {
                "bucket": self.config.client.input_bucket,
                "path": path,
                "video": path.rsplit("/", 1)[-1],
            } for path in paths
        ]
        self.deps.yt_client.write_table(
            table_path=self.config.client.output_table,
            rows=rows
        )

        return debug
