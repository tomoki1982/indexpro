# 仕入先検索アプリ 更新手順書

この手順書は、個人PCで更新担当者が `indexPro 仕入先検索` の公開版を更新するときに使います。

対象公開URL:
- `https://indexpro-search.streamlit.app/`

## 前提

- 公開版は Streamlit で動いている
- 元データは Googleスプレッドシート側にある
- 更新担当者は個人PCで作業する
- 利用者は公開URLを見るだけ

## 更新作業の流れ

### 1. 元データを更新する

まず、Googleスプレッドシートの元データを更新します。

例:
- メーカー一覧
- 代理店・取扱店一覧
- 取扱メーカー一覧
- メーカー別関係一覧

### 2. ローカルで確認する

必要に応じて、個人PCでローカル画面を開いて確認します。

実行方法:
- `batch\run_ui.bat`

確認項目:
- メーカー検索
- 代理店・取扱店検索
- 推定代理店検索
- 推定競合検索

### 3. コード修正がある場合だけ GitHub に反映する

画面やロジックを修正した場合は、GitHub に反映します。

実行方法:
- `batch\push_to_github.bat`

補足:
- データだけ更新した場合は、この手順は不要です

### 4. GitHub Actions を実行する

GitHub のリポジトリを開いて、`Actions` タブから `Manual Redeploy Streamlit` を実行します。

すぐ開きたい場合:
- `batch\open_actions_page.bat`

手順:
1. GitHub で `tomoki1982/indexpro` を開く
2. `Actions` タブを開く
3. `Manual Redeploy Streamlit` を選ぶ
4. `Run workflow` を押す
5. 必要なら更新メモを入れて実行する

### 5. 公開版を確認する

GitHub Actions 完了後、次のURLを開きます。

- `https://indexpro-search.streamlit.app/`

確認項目:
- アプリが正常に開く
- 各検索が正常に動く
- 最終更新日が想定どおり

## 更新パターンごとの使い分け

### データだけ更新した場合

1. Googleスプレッドシート更新
2. GitHub Actions 実行
3. 公開版確認

### コードも更新した場合

1. コード修正
2. `batch\push_to_github.bat`
3. GitHub Actions 実行
4. 公開版確認

## 更新担当者が覚えること

基本はこの一行です。

`データ更新 -> 必要ならローカル確認 -> 必要なら GitHub push -> Actions 実行 -> 公開版確認`
