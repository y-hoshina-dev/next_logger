# Next Logger Release Readiness

最終更新: 2026-02-28
対象: `next_logger`

## 自動検証結果
- [x] `python -m unittest discover -s tests -p "test_*.py" -v` 成功
- [x] Python構文チェック成功
- [x] `scripts/release_check.ps1` 成功
- [x] `scripts/build_exe.ps1` 成功（`dist/next_logger.exe` 出力確認）
- [x] `dist/next_logger.exe` のローカル起動確認（短時間）
- [x] 再接続バックオフ計算テスト追加
- [x] 保持ポリシーテスト追加
- [x] manifest再接続履歴テスト追加

## 実装完了項目
- [x] 状態機械ベースの制御
- [x] 開始前プリフライト
- [x] セッション単位ログ保存 + manifest
- [x] 自動再接続（fixed/exponential）
- [x] ログ保持ポリシー（件数/日数）
- [x] 初回セットアップウィザード
- [x] プロファイル保存/読込/削除
- [x] 復旧マーカー通知

## 未完了（手動確認が必要）
- [ ] 実機シリアル機器でE2E試験
- [ ] EXE起動確認（配布先PCでの動作確認）
- [ ] リリース判定会（重大不具合0件確認）

## 実機E2E参照
- `docs/E2E_TEST_CHECKLIST.md` を使用
