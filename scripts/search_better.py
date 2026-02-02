#!/usr/bin/env python3
"""
Search Better - ウェブ検索で改善候補を発見

Usage:
    python scripts/search_better.py --requirements <requirements.json>
    python scripts/search_better.py --query "gpu cloud pricing 2026"

Note:
    このスクリプトはエージェントがWebSearch/WebFetchツールを使う際の
    ガイドラインを提供する。実際の検索はエージェントが行う。
"""

import sys
import json
import argparse
from datetime import datetime


def generate_search_queries(requirements: dict) -> list[dict]:
    """
    要件に基づいて検索クエリを生成

    エージェントはこれらのクエリでウェブ検索を行い、
    結果を解析して改善候補を見つける。
    """
    queries = []
    current_year = datetime.now().year

    # GPU要件がある場合
    if requirements.get("needs_gpu"):
        queries.extend([
            {
                "query": f"cheapest gpu cloud {current_year}",
                "purpose": "cost_reduction",
                "extract": ["provider_name", "gpu_type", "price_per_hour"],
            },
            {
                "query": f"gpu cloud comparison vast.ai runpod lambda {current_year}",
                "purpose": "provider_comparison",
                "extract": ["provider_name", "pros", "cons", "pricing"],
            },
        ])

        # 特定のGPUタイプ
        gpu_type = requirements.get("gpu_type", "")
        if gpu_type:
            queries.append({
                "query": f"{gpu_type} cloud rental price {current_year}",
                "purpose": "specific_gpu_pricing",
                "extract": ["provider_name", "price_per_hour"],
            })

    # 言語固有のツール検索
    language = requirements.get("primary_language", "")
    if language == "python":
        queries.extend([
            {
                "query": f"best python package manager {current_year}",
                "purpose": "tool_improvement",
                "extract": ["tool_name", "advantages", "installation"],
                "note": "uv is recommended over pip for speed",
            },
            {
                "query": f"python deployment best practices {current_year}",
                "purpose": "best_practices",
                "extract": ["practice", "reason"],
            },
        ])

    # フレームワーク固有
    for framework in requirements.get("frameworks", []):
        queries.append({
            "query": f"best way to deploy {framework} {current_year}",
            "purpose": "framework_deployment",
            "extract": ["method", "provider", "considerations"],
        })

    # 一般的なVPS検索
    if not requirements.get("needs_gpu"):
        queries.append({
            "query": f"cheapest vps {current_year} comparison",
            "purpose": "cost_reduction",
            "extract": ["provider_name", "specs", "price_per_month"],
        })

    return queries


def analyze_search_results(results: list[dict], current_record: dict | None) -> list[dict]:
    """
    検索結果を分析して改善候補を生成

    この関数はエージェントが検索結果を取得した後に呼び出され、
    過去の記録と比較して改善候補を提案する。
    """
    improvements = []

    current_cost = current_record.get("estimated_cost", float("inf")) if current_record else float("inf")
    current_provider = current_record.get("provider_used", "") if current_record else ""

    for result in results:
        # コスト比較
        if "price_per_hour" in result:
            price = result["price_per_hour"]
            if price < current_cost * 0.7:  # 30%以上安い
                savings = (1 - price / current_cost) * 100 if current_cost != float("inf") else 0
                improvements.append({
                    "type": "cost_reduction",
                    "title": f"Cheaper provider: {result.get('provider_name', 'Unknown')}",
                    "description": f"Found {savings:.0f}% cheaper option",
                    "current_value": f"${current_cost:.4f}/hour",
                    "suggested_value": f"${price:.4f}/hour",
                    "source": result.get("source_url", ""),
                    "priority": 70 if savings > 30 else 50,
                })

        # 新しいプロバイダー
        provider = result.get("provider_name", "")
        if provider and provider != current_provider:
            improvements.append({
                "type": "alternative_provider",
                "title": f"Alternative: {provider}",
                "description": result.get("description", ""),
                "source": result.get("source_url", ""),
                "priority": 40,
            })

        # ツール改善
        if result.get("purpose") == "tool_improvement":
            improvements.append({
                "type": "tool_upgrade",
                "title": f"Recommended tool: {result.get('tool_name', 'Unknown')}",
                "description": result.get("advantages", ""),
                "priority": 60,
            })

    # 優先度でソート
    improvements.sort(key=lambda x: x.get("priority", 0), reverse=True)

    return improvements


def main():
    parser = argparse.ArgumentParser(description="Search Better - Find improvements via web search")
    parser.add_argument("--requirements", help="Requirements JSON file or inline JSON")
    parser.add_argument("--query", help="Direct search query")
    parser.add_argument("--current-record", help="Current record JSON for comparison")

    args = parser.parse_args()

    if args.requirements:
        # 要件からクエリを生成
        if args.requirements.startswith("{"):
            requirements = json.loads(args.requirements)
        else:
            from pathlib import Path
            requirements = json.loads(Path(args.requirements).read_text())

        queries = generate_search_queries(requirements)

        output = {
            "action": "web_search_required",
            "queries": queries,
            "instructions": """
エージェントは以下の手順で検索を実行してください:

1. 各クエリでWebSearchツールを使用
2. 結果からextractフィールドの情報を抽出
3. 抽出した情報をこのスクリプトに戻して分析:
   python scripts/search_better.py --analyze-results <results.json>

または、エージェントが直接結果を解析して改善候補を判断することも可能です。
""",
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    elif args.query:
        # 直接クエリの場合
        output = {
            "action": "web_search_required",
            "queries": [{"query": args.query, "purpose": "custom"}],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
