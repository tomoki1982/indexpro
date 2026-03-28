# indexPro 仕入先検索アプリ

`indexPro` の公開情報をもとに、メーカー、代理店・取扱店、推定代理店、推定競合を検索する Streamlit アプリです。

## 現在の運用

- 利用者は公開URLを使う
- 更新担当者は個人PCで元データを更新する
- 必要ならローカル確認する
- GitHub Actions を手動実行して公開版を再反映する

公開URL:
- [indexpro-search.streamlit.app](https://indexpro-search.streamlit.app/)

## 主なファイル

- UI: `app/ui.py`
- 推定代理店ロジック: `app/agent_inference.py`
- 推定競合ロジック: `app/competitor_inference.py`
- 起動バッチ: `batch/run_ui.bat`
- GitHub反映バッチ: `batch/push_to_github.bat`
- 更新手順書: `docs/update_runbook.md`

## ローカル起動

```powershell
cd /d C:\Users\gotta\.codex\codexアプリ\仕入先検索アプリ
pip install -r requirements.txt
streamlit run app/ui.py
```

## 更新の流れ

1. Googleスプレッドシートの元データを更新
2. 必要なら `batch/run_ui.bat` でローカル確認
3. コード修正がある場合だけ `batch/push_to_github.bat`
4. GitHub Actions の `Manual Redeploy Streamlit` を実行
5. 公開URLで確認

詳細は `docs/update_runbook.md` を参照してください。
