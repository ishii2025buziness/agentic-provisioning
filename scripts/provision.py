#!/usr/bin/env python3
"""
Provision - 環境をプロビジョニング

Usage:
    python scripts/provision.py --provider docker-local --repo <github-url>
    python scripts/provision.py --provider docker-local --requirements <requirements.json>

Providers:
    - docker-local: ローカルDocker環境
    - (将来) vast-ai, runpod, hetzner, etc.
"""

import sys
import json
import subprocess
import tempfile
import uuid
import argparse
from pathlib import Path
from datetime import datetime


def provision_docker_local(repo_url: str, requirements: dict) -> dict:
    """
    ローカルDockerでプロビジョニング
    """
    result = {
        "provider_name": "docker-local",
        "instance_id": f"ap-{uuid.uuid4().hex[:8]}",
        "status": "provisioning",
        "setup_steps": [],
        "logs": [],
        "errors": [],
        "created_at": datetime.now().isoformat(),
        "cost_per_hour": 0.0,
    }

    try:
        # Step 1: リポジトリをクローン
        result["setup_steps"].append("Cloning repository...")

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, tmpdir],
                capture_output=True,
                text=True,
            )

            if clone_result.returncode != 0:
                result["status"] = "failed"
                result["errors"].append(f"Clone failed: {clone_result.stderr}")
                return result

            result["logs"].append(f"Cloned to {tmpdir}")

            # Step 2: Dockerfileの確認
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            has_dockerfile = dockerfile_path.exists()

            if has_dockerfile:
                result["setup_steps"].append("Building from existing Dockerfile...")
            else:
                result["setup_steps"].append("Generating Dockerfile...")
                # 言語に応じたDockerfileを生成
                dockerfile_content = generate_dockerfile(requirements)
                dockerfile_path.write_text(dockerfile_content)
                result["logs"].append("Generated Dockerfile")

            # Step 3: イメージをビルド
            image_name = f"ap-{requirements.get('repo_name', 'project')}:latest"
            result["setup_steps"].append(f"Building image: {image_name}")

            build_result = subprocess.run(
                ["docker", "build", "-t", image_name, tmpdir],
                capture_output=True,
                text=True,
            )

            if build_result.returncode != 0:
                result["status"] = "failed"
                result["errors"].append(f"Build failed: {build_result.stderr}")
                return result

            result["image_name"] = image_name
            result["logs"].append("Image built successfully")

            # Step 4: コンテナを起動
            result["setup_steps"].append("Starting container...")

            run_cmd = ["docker", "run", "-d", "--name", result["instance_id"]]

            # GPU対応
            if requirements.get("needs_gpu"):
                run_cmd.extend(["--gpus", "all"])

            # ポートマッピング
            for port in requirements.get("ports", []):
                run_cmd.extend(["-p", f"{port}:{port}"])

            run_cmd.append(image_name)

            run_result = subprocess.run(run_cmd, capture_output=True, text=True)

            if run_result.returncode != 0:
                result["status"] = "failed"
                result["errors"].append(f"Run failed: {run_result.stderr}")
                return result

            result["container_id"] = run_result.stdout.strip()[:12]
            result["status"] = "running"
            result["ready_at"] = datetime.now().isoformat()
            result["logs"].append(f"Container started: {result['container_id']}")

    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(str(e))

    return result


def generate_dockerfile(requirements: dict) -> str:
    """要件に基づいてDockerfileを生成"""
    language = requirements.get("primary_language", "python")

    if language == "python":
        base_image = "python:3.11-slim"
        if requirements.get("needs_gpu"):
            base_image = "nvidia/cuda:12.1-runtime-ubuntu22.04"

        return f"""FROM {base_image}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Copy requirements
COPY requirements.txt* pyproject.toml* ./

# Install dependencies
RUN if [ -f requirements.txt ]; then uv pip install --system -r requirements.txt; fi
RUN if [ -f pyproject.toml ]; then uv pip install --system .; fi

# Copy application
COPY . .

# Default command
CMD ["python", "{requirements.get('entry_point', 'main.py')}"]
"""

    elif language in ["javascript", "typescript"]:
        return """FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["npm", "start"]
"""

    elif language == "go":
        return """FROM golang:1.21-alpine

WORKDIR /app

COPY go.* ./
RUN go mod download

COPY . .
RUN go build -o main .

CMD ["./main"]
"""

    else:
        return """FROM ubuntu:22.04

WORKDIR /app
COPY . .

CMD ["/bin/bash"]
"""


def terminate_container(instance_id: str) -> dict:
    """コンテナを停止・削除"""
    result = {"success": False, "instance_id": instance_id}

    try:
        # 停止
        subprocess.run(["docker", "stop", instance_id], capture_output=True)
        # 削除
        subprocess.run(["docker", "rm", instance_id], capture_output=True)
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(description="Provision environments")
    parser.add_argument("--provider", default="docker-local", help="Provider to use")
    parser.add_argument("--repo", help="GitHub repository URL")
    parser.add_argument("--requirements", help="Requirements JSON")
    parser.add_argument("--terminate", help="Terminate instance by ID")

    args = parser.parse_args()

    if args.terminate:
        result = terminate_container(args.terminate)
        print(json.dumps(result, indent=2))
        return

    if not args.repo and not args.requirements:
        parser.print_help()
        sys.exit(1)

    # 要件を読み込み
    if args.requirements:
        if args.requirements.startswith("{"):
            requirements = json.loads(args.requirements)
        else:
            requirements = json.loads(Path(args.requirements).read_text())
    else:
        # リポジトリURLから要件を取得（analyze_repo を呼び出す）
        analyze_result = subprocess.run(
            ["python", str(Path(__file__).parent / "analyze_repo.py"), args.repo],
            capture_output=True,
            text=True,
        )
        if analyze_result.returncode != 0:
            print(json.dumps({"error": "Failed to analyze repo", "details": analyze_result.stderr}))
            sys.exit(1)
        requirements = json.loads(analyze_result.stdout)

    repo_url = args.repo or requirements.get("repo_url", "")

    if args.provider == "docker-local":
        result = provision_docker_local(repo_url, requirements)
    else:
        result = {
            "error": f"Unknown provider: {args.provider}",
            "available_providers": ["docker-local"],
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
