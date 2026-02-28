# Next Logger (再設計版)

## 概要
- `serial_logger_GUI3` の次世代実装。
- UIと受信処理を分離し、状態機械で操作を制御。
- ログ欠損可視化、プリフライト、復旧マーカー、プロファイル保存に対応。

## 実行方法
1. `cd next_logger`
2. `pip install -r requirements.txt`
3. `python app.py`

## 補助スクリプト
- `scripts/release_check.ps1`: 単体テスト + 構文チェック
- `scripts/build_exe.ps1`: Windows向けEXEビルド

## 主な機能
- 3ペインUI（接続設定 / ライブログ / セッション設定）
- `Start / Pause / Resume / Stop` の状態連動制御
- 開始前プリフライト（保存先書込、設定値、フォーマット）
- セッション単位出力（`raw_partNN.log`, `data_partNN.*`, `error_partNN.log`, `manifest.json`）
- 欠損行数・保存失敗数・受信レートの可視化
- 自動再接続（回数/待機秒数の設定）
- ログ保持ポリシー（保持セッション数/保持日数）
- 異常終了時の復旧マーカー通知
- 設定プロファイル保存/読込/削除
- 初回セットアップウィザード

## ディレクトリ構成
- `next_logger/domain`: 状態機械・モデル
- `next_logger/application`: ユースケース・プリフライト
- `next_logger/infrastructure`: シリアルI/O・ファイル書込・永続化
- `next_logger/presentation`: PySide6 UI
- `docs/E2E_TEST_CHECKLIST.md`: 手動E2E試験とリリース判定
- `docs/RELEASE_READINESS.md`: 自動検証結果と未完了項目

## 補足
- 初期版としてP0/P1の主要項目を先行実装しています。
- 実機E2EとEXE最終配布手順は `docs/E2E_TEST_CHECKLIST.md` の完了が必要です。
