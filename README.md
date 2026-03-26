# 仕入先検索アプリ

現在の用途は `indexPro` の一覧収集と検証です。

今後 UI に進む前提で、プロジェクトは次の2系統に分けています。

- 現在使うもの
  - `indexPro` のメーカー一覧名取得
  - `indexPro` の代理店・取扱店一覧名取得
  - 代理店・取扱店ごとの取扱メーカー一覧取得
  - 取得結果の検証
- いったん使わないもの
  - 過去の汎用Web収集試作
  - オムロン単体試験の試作コード

## 現在使うフォルダ

```text
仕入先検索アプリ/
├─ app/
│  ├─ cli.py
│  ├─ indexpro_directory.py
│  ├─ indexpro_directory_pipeline.py
│  ├─ indexpro_directory_reporting.py
│  ├─ indexpro_directory_validation.py
│  ├─ models.py
│  ├─ settings.py
│  └─ storage.py
├─ data/
│  └─ fixtures/
│     └─ indexpro_directory_sample.json
├─ output/
│  ├─ db/
│  ├─ indexpro/
│  │  ├─ listings/
│  │  └─ validation/
│  └─ trials/
├─ tests/
│  ├─ test_indexpro_directory_fixture.py
│  └─ test_indexpro_directory_parser.py
├─ README.md
└─ requirements.txt
```

## 使わないものの退避先

```text
仕入先検索アプリ/
├─ app/archive/
├─ data/archive/
└─ tests/archive/
```

ここには過去の試作コードを退避しています。今後の UI 開発では基本的に見なくて大丈夫です。

## 実行方法

Anaconda Prompt を前提にしています。

```powershell
cd /d C:\Users\gotta\.codex\codexアプリ\仕入先検索アプリ
pip install -r requirements.txt
```

### 1. indexPro 一覧収集

```powershell
python -m app.cli --mode indexpro-directory-live --crawl-delay 0.2
```

### 2. indexPro 一覧検証

```powershell
python -m app.cli --mode indexpro-directory-validate
```

### 3. fixture で軽く確認

```powershell
python -m app.cli --mode indexpro-directory-fixture
```

## 出力先

### 一覧収集結果

`output/indexpro/listings/`

- `indexpro_directory_manufacturers.csv`
- `indexpro_directory_distributors.csv`
- `indexpro_directory_handlings.csv`
- `indexpro_directory_metrics.csv`

### 検証結果

`output/indexpro/validation/`

- `indexpro_validation_summary.csv`
- `indexpro_validation_duplicate_dids.csv`
- `indexpro_validation_name_variants.csv`
- `indexpro_validation_match_metrics.csv`
- `indexpro_validation_unmatched_handlings.csv`

### DB

`output/db/supplier_flow.db`

## 現在の確認ポイント

### 一覧収集が成功しているか

`output/indexpro/listings/indexpro_directory_metrics.csv` を見ます。

- `manufacturer_count`
- `distributor_count`
- `handling_relation_count`

### 検証が成功しているか

`output/indexpro/validation/indexpro_validation_summary.csv` を見ます。

- `duplicate_did_groups`
- `distributor_name_variant_groups`
- `handling_unmatched`

## 次のステップ

次は UI を使います。

最小UIは次の2画面です。

- メーカーから代理店・取扱店一覧を検索
- 代理店・取扱店から取扱メーカー一覧を検索

## UI 起動

```powershell
streamlit run app/ui.py
```

起動後にブラウザで、次を確認できます。

- メーカー名を入れて、そのメーカーを扱う代理店・取扱店を一覧表示
- 代理店・取扱店名を入れて、その会社の取扱メーカー一覧を表示
