# Copyright 2026 GFT Technologies SE.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deploy the SDLC orchestration workflow to Vertex AI Agent Engine.

Follows the adk-samples deployment convention:

    python deployment/deploy.py --create
    python deployment/deploy.py --list
    python deployment/deploy.py --delete --resource_id=<AGENT_ENGINE_ID>

Requires the real ADK runtime and Vertex AI:

    pip install -r requirements-real.txt google-cloud-aiplatform[adk,agent_engines]

Environment (see .env.example):
    GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, GOOGLE_CLOUD_STORAGE_BUCKET
"""

from __future__ import annotations

import argparse
import os
import sys

# Agent Engine deploys the real ADK orchestration; ensure agent.py builds the
# SequentialAgent/ParallelAgent graph (not the offline stub) on import.
os.environ.setdefault("SDLC_MODE", "real")


def _init_vertex() -> tuple[str, str, str]:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    bucket = os.environ.get("GOOGLE_CLOUD_STORAGE_BUCKET")
    if not project:
        sys.exit("GOOGLE_CLOUD_PROJECT is required.")
    if not bucket:
        sys.exit("GOOGLE_CLOUD_STORAGE_BUCKET is required (staging bucket, no gs:// prefix).")

    import vertexai

    vertexai.init(project=project, location=location, staging_bucket=f"gs://{bucket}")
    return project, location, bucket


def create() -> None:
    """Package the workflow and create a remote Agent Engine instance."""
    _init_vertex()
    from vertexai import agent_engines
    from vertexai.preview.reasoning_engines import AdkApp

    from sdlc_workflow.agent import root_agent

    app = AdkApp(agent=root_agent, enable_tracing=True)
    remote_agent = agent_engines.create(
        app,
        display_name="wynxx-sdlc-orchestration",
        description="ADK 2.0 graph workflow over the Wynxx MCP server.",
        requirements=[
            "google-adk>=2.0",
            "mcp>=1.0,<2.0",
            "pydantic>=2.7,<3.0",
            "pydantic-settings>=2.3,<3.0",
        ],
        extra_packages=["./sdlc_workflow"],
    )
    print(f"Created Agent Engine: {remote_agent.resource_name}")


def delete(resource_id: str) -> None:
    _init_vertex()
    from vertexai import agent_engines

    agent_engines.get(resource_id).delete(force=True)
    print(f"Deleted Agent Engine: {resource_id}")


def list_agents() -> None:
    _init_vertex()
    from vertexai import agent_engines

    agents = list(agent_engines.list())
    if not agents:
        print("No deployed agents found.")
        return
    print("Deployed agents:")
    for a in agents:
        print(f"  {a.display_name}: {a.resource_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy the SDLC workflow to Agent Engine.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true", help="Create a new deployment.")
    group.add_argument("--delete", action="store_true", help="Delete an existing deployment.")
    group.add_argument("--list", action="store_true", help="List deployments.")
    parser.add_argument("--resource_id", help="Agent Engine resource id (for --delete).")
    args = parser.parse_args()

    if args.create:
        create()
    elif args.delete:
        if not args.resource_id:
            sys.exit("--delete requires --resource_id")
        delete(args.resource_id)
    elif args.list:
        list_agents()


if __name__ == "__main__":
    main()
