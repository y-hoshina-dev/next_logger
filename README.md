-----
serial_logger_GUI/
├── app.py                ← メイン実行ファイル（GUI起動）
├── logger/               ← ロガー関連の処理をモジュール化
│   ├── __init__.py
│   ├── serial_reader.py  ← シリアルポートの読み取り処理
│   └── file_writer.py    ← ログファイルの保存処理
├── logs/                 ← ログファイルの保存先（.gitignore対象）
├── config.ini            ← 設定ファイル（ポートなどを外部定義）
├── .gitignore            ← ログ除外など
├── requirements.txt      ← 必要なライブラリ一覧
└── README.md             ← 簡単な説明書（任意）
-----
app.py:TkinterのGUIを起動するメインスクリプト。ロジック部分は logger モジュールに任せます。
logger:実際の処理ロジックをまとめるフォルダ。モジュール化してGUIと分離します。
serial_reader.py:pyserialを使ってシリアルデータを受信する関数を記述します。
file_writer.py:	ログファイルにデータを書き込む関数を記述します。
__init__.py:モジュールとしてインポート可能にするファイル（中身は空でもOK）
logs/:	実行時に生成されるログファイルの保存フォルダ。.gitignoreで除外します。
config.ini:設定値（COMポート名、保存先、ボーレートなど）を記述しておくと便利です。
requirements.txt:必要なライブラリをまとめておくと他の環境で再現できます。
README.md:簡単な使い方や依存関係の説明を記載しておくと親切です。
