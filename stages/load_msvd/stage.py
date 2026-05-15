import json

from yt_framework.core.pipeline import DebugContext
from yt_framework.core.stage import BaseStage
from yt_framework.utils.env import load_secrets
from ytjobs.s3.client import S3Client
from yt_framework.yt.clients.yql.yql_requests import JoinTablesRequest


class LoadMSVDStage(BaseStage):
    def __init__(self, deps, logger):
        super().__init__(deps, logger)

        self.s3_client = S3Client.create(
            secrets=load_secrets(self.deps.configs_dir),
            client_type="download",
        )

    def run(self, debug: DebugContext) -> DebugContext:
        raw = self.s3_client.download_by_uri(self.config.client.json_s3_uri)
        data = json.loads(raw)

        rows = [
            {
                "video": video["video"],
                "caption": video["caption"],
            } for video in data
        ]
        self.deps.yt_client.write_table(
            table_path=self.config.client.output_table,
            rows=rows
        )

        self.deps.yt_client.join_tables_request(
            JoinTablesRequest(
                left_table=self.config.client.s3_paths_table,
                right_table=self.config.client.output_table,
                output_table=self.config.client.joined_table,
                on="video",
                how="inner",
                select_columns=[
                    "a.bucket AS bucket",
                    "a.path AS path",
                    "b.video AS video",
                    "b.caption AS caption"
                ],
            )
        )

        return debug
