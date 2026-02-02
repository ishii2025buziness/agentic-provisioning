#!/usr/bin/env python3
"""
Repository Analyzer - GitHubリポジトリから要件を自動抽出

Usage:
    python scripts/analyze_repo.py <github-url>
    python scripts/analyze_repo.py https://github.com/user/repo

Output:
    JSON形式で要件を出力
"""

import sys
import json
import re
import httpx


def parse_github_url(url: str) -> tuple[str, str]:
    """GitHubのURLからオーナーとリポジトリ名を抽出"""
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\.]+)",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).rstrip(".git")
    raise ValueError(f"Invalid GitHub URL: {url}")


def analyze(repo_url: str) -> dict:
    """リポジトリを解析して要件を抽出"""
    owner, repo_name = parse_github_url(repo_url)

    requirements = {
        "repo_url": repo_url,
        "repo_name": repo_name,
        "owner": owner,
        "primary_language": "unknown",
        "language_version": None,
        "frameworks": [],
        "has_dockerfile": False,
        "has_docker_compose": False,
        "has_requirements_txt": False,
        "has_pyproject_toml": False,
        "has_package_json": False,
        "needs_gpu": False,
        "gpu_type": None,
        "estimated_memory_gb": 2.0,
        "estimated_storage_gb": 10.0,
        "entry_point": None,
        "ports": [],
        "confidence_score": 0.3,
        "analysis_notes": [],
    }

    # GPU要件を示すキーワード
    GPU_KEYWORDS = [
        "torch", "pytorch", "tensorflow", "jax", "cuda", "gpu",
        "nvidia", "cudnn", "transformers", "diffusers", "accelerate",
    ]

    # MLフレームワーク
    ML_FRAMEWORKS = [
        "torch", "tensorflow", "jax", "transformers", "diffusers",
        "langchain", "llama", "vllm", "huggingface",
    ]

    try:
        with httpx.Client(timeout=30.0) as client:
            # リポジトリ情報を取得
            resp = client.get(f"https://api.github.com/repos/{owner}/{repo_name}")
            resp.raise_for_status()
            repo_info = resp.json()

            requirements["primary_language"] = (repo_info.get("language") or "unknown").lower()
            default_branch = repo_info.get("default_branch", "main")

            # ファイルツリーを取得
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}",
                params={"recursive": "1"}
            )
            resp.raise_for_status()
            files = [item["path"] for item in resp.json().get("tree", []) if item["type"] == "blob"]
            files_lower = {f.lower() for f in files}

            # ファイル構造を解析
            requirements["has_requirements_txt"] = "requirements.txt" in files
            requirements["has_pyproject_toml"] = "pyproject.toml" in files
            requirements["has_package_json"] = "package.json" in files
            requirements["has_dockerfile"] = "dockerfile" in files_lower
            requirements["has_docker_compose"] = any(
                "docker-compose" in f.lower() or "compose.yaml" in f.lower()
                for f in files
            )

            # エントリーポイントの推測
            for candidate in ["main.py", "app.py", "run.py", "server.py", "index.js", "main.go"]:
                if candidate in files:
                    requirements["entry_point"] = candidate
                    break

            # requirements.txt を解析
            if requirements["has_requirements_txt"]:
                try:
                    resp = client.get(
                        f"https://raw.githubusercontent.com/{owner}/{repo_name}/{default_branch}/requirements.txt"
                    )
                    content = resp.text.lower()

                    for keyword in GPU_KEYWORDS:
                        if keyword in content:
                            requirements["needs_gpu"] = True
                            requirements["gpu_type"] = "CUDA"
                            requirements["analysis_notes"].append(f"GPU requirement detected: {keyword}")
                            break

                    for framework in ML_FRAMEWORKS:
                        if framework in content and framework not in requirements["frameworks"]:
                            requirements["frameworks"].append(framework)

                    # メモリ推定
                    if any(fw in content for fw in ["transformers", "diffusers", "vllm"]):
                        requirements["estimated_memory_gb"] = 16.0
                    elif any(fw in content for fw in ["torch", "tensorflow"]):
                        requirements["estimated_memory_gb"] = 8.0

                except Exception:
                    pass

            # 信頼度を計算
            score = 0.3
            if requirements["primary_language"] != "unknown":
                score += 0.2
            if requirements["has_requirements_txt"] or requirements["has_pyproject_toml"]:
                score += 0.2
            if requirements["has_dockerfile"]:
                score += 0.2
            if requirements["entry_point"]:
                score += 0.1
            requirements["confidence_score"] = min(score, 1.0)

    except Exception as e:
        requirements["analysis_notes"].append(f"Error: {str(e)}")
        requirements["confidence_score"] = 0.1

    return requirements


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_repo.py <github-url>", file=sys.stderr)
        sys.exit(1)

    repo_url = sys.argv[1]

    # URLの正規化
    if not repo_url.startswith("http"):
        repo_url = f"https://github.com/{repo_url}"

    result = analyze(repo_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
