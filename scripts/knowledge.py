#!/usr/bin/env python3
"""
Knowledge Base - 成功体験のLock & Search Better

Usage:
    python scripts/knowledge.py get <github-url>
    python scripts/knowledge.py save --repo <url> --result <result.json>
    python scripts/knowledge.py list
    python scripts/knowledge.py similar --requirements <requirements.json>
"""

import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
import argparse


# ナレッジベースのストレージパス
KNOWLEDGE_DIR = Path(__file__).parent.parent / "assets" / "knowledge"


def ensure_dir():
    """ストレージディレクトリを確保"""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    index_file = KNOWLEDGE_DIR / "index.json"
    if not index_file.exists():
        index_file.write_text(json.dumps({"records": {}, "repo_mapping": {}}, indent=2))


def load_index() -> dict:
    """インデックスを読み込む"""
    ensure_dir()
    return json.loads((KNOWLEDGE_DIR / "index.json").read_text())


def save_index(index: dict):
    """インデックスを保存"""
    (KNOWLEDGE_DIR / "index.json").write_text(json.dumps(index, indent=2, default=str))


def repo_key(repo_url: str) -> str:
    """リポジトリURLから一意のキーを生成"""
    normalized = repo_url.lower().rstrip("/").rstrip(".git")
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def get_last_success(repo_url: str) -> dict | None:
    """指定リポジトリの最後の成功記録を取得"""
    index = load_index()
    key = repo_key(repo_url)
    record_ids = index["repo_mapping"].get(key, [])

    for record_id in reversed(record_ids):
        record_info = index["records"].get(record_id, {})
        if record_info.get("success", False):
            record_file = KNOWLEDGE_DIR / f"{record_id}.json"
            if record_file.exists():
                return json.loads(record_file.read_text())

    return None


def save_record(repo_url: str, result: dict) -> str:
    """成功した手順を保存"""
    ensure_dir()
    index = load_index()
    key = repo_key(repo_url)
    record_id = f"{key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # レコードを作成
    record = {
        "id": record_id,
        "repo_url": repo_url,
        "created_at": datetime.now().isoformat(),
        **result,
    }

    # ファイルに保存
    record_file = KNOWLEDGE_DIR / f"{record_id}.json"
    record_file.write_text(json.dumps(record, indent=2, default=str))

    # インデックスを更新
    if key not in index["repo_mapping"]:
        index["repo_mapping"][key] = []
    index["repo_mapping"][key].append(record_id)
    index["records"][record_id] = {
        "repo_url": repo_url,
        "provider": result.get("provider_used", "unknown"),
        "success": result.get("success", True),
        "created_at": record["created_at"],
    }
    save_index(index)

    return record_id


def list_records() -> list[dict]:
    """全記録を一覧"""
    index = load_index()
    return [
        {"id": rid, **info}
        for rid, info in index["records"].items()
    ]


def find_similar(requirements: dict) -> list[dict]:
    """類似の要件を持つ過去のセットアップを検索"""
    index = load_index()
    similar = []

    for record_id, record_info in index["records"].items():
        if not record_info.get("success", False):
            continue

        record_file = KNOWLEDGE_DIR / f"{record_id}.json"
        if not record_file.exists():
            continue

        record = json.loads(record_file.read_text())
        record_req = record.get("requirements", {})

        # 類似度を計算
        similarity = calculate_similarity(requirements, record_req)
        if similarity > 0.5:
            similar.append({
                "record": record,
                "similarity": similarity,
            })

    similar.sort(key=lambda x: x["similarity"], reverse=True)
    return similar


def calculate_similarity(req1: dict, req2: dict) -> float:
    """2つの要件の類似度を計算"""
    if not req1 or not req2:
        return 0.0

    # 重要なキーで比較
    keys = ["primary_language", "needs_gpu", "has_dockerfile"]
    matches = sum(1 for k in keys if req1.get(k) == req2.get(k))

    # フレームワークの重複
    fw1 = set(req1.get("frameworks", []))
    fw2 = set(req2.get("frameworks", []))
    if fw1 and fw2:
        fw_similarity = len(fw1 & fw2) / len(fw1 | fw2)
        return (matches / len(keys) + fw_similarity) / 2

    return matches / len(keys) if keys else 0.0


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # get コマンド
    get_parser = subparsers.add_parser("get", help="Get last successful record for a repo")
    get_parser.add_argument("repo_url", help="GitHub repository URL")

    # save コマンド
    save_parser = subparsers.add_parser("save", help="Save a provisioning result")
    save_parser.add_argument("--repo", required=True, help="Repository URL")
    save_parser.add_argument("--result", required=True, help="Result JSON file or inline JSON")

    # list コマンド
    subparsers.add_parser("list", help="List all records")

    # similar コマンド
    similar_parser = subparsers.add_parser("similar", help="Find similar setups")
    similar_parser.add_argument("--requirements", required=True, help="Requirements JSON file or inline JSON")

    args = parser.parse_args()

    if args.command == "get":
        result = get_last_success(args.repo_url)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"found": False, "message": "No successful record found"}))

    elif args.command == "save":
        # JSON入力を処理
        if args.result.startswith("{"):
            result = json.loads(args.result)
        else:
            result = json.loads(Path(args.result).read_text())

        record_id = save_record(args.repo, result)
        print(json.dumps({"success": True, "record_id": record_id}))

    elif args.command == "list":
        records = list_records()
        print(json.dumps(records, indent=2, ensure_ascii=False))

    elif args.command == "similar":
        if args.requirements.startswith("{"):
            requirements = json.loads(args.requirements)
        else:
            requirements = json.loads(Path(args.requirements).read_text())

        similar = find_similar(requirements)
        print(json.dumps(similar, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
