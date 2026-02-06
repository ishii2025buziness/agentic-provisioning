# Knowledge Base

このディレクトリにはプロビジョニング結果の記録が保存されます。

## ファイル構成

- `index.json` — 全記録のインデックス
- `{record_id}.json` — 個別のプロビジョニング記録

## 注意

`*.json` ファイルはユーザー固有データのため `.gitignore` で除外されています。
初回実行時に自動生成されます。

## シードデータ

初回セットアップ時に `seed/` 配下のファイルを `assets/knowledge/` にコピーすることで、
過去の障害事例から学んだ知識をプリロードできます。

```bash
cp assets/knowledge/seed/*.json assets/knowledge/
```
