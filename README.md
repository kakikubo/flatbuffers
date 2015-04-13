# KMS tool リポジトリ

Asset パイプライン用のスクリプトなどをおいています

ビルド用の Jenkins マシンや開発用の PHP サーバで動くものがメインになります

# jenkins マシンでの差分監視と自動コミット
以下のような構成で、box sync にファイルを投げ込むと、数秒後に自動で gitlab の kms/asset が更新されます

```
master
 each user                ffl.jenkins (Jenkins PC)                                      git (Jenkins PC)
 +-------------------+    +--------------------------------------------------------+    +-----------+
 | Box Sync          | -> | Box Sync         -> watchman -> build.py -> git commit | -> | gitlab    |
 | kms_master_asset  |    | kms_master_asset                            git push   |    | kms/asset |
 +-------------------+    +--------------------------------------------------------+    +-----------+

working
 each user                ffl.jenkins (Jenkins PC)                                      git (Jenkins PC)
 +-------------------+    +-------------------------------------------------------------------------+
 | Box Sync          | -> | Box Sync         -> watchman -> build.py -> Box Sync                    |
 | kms_xxx.yyy_asset |    | kms_xxx.yyy_asset                           kms_xxx.yyy_asset_generated |
 +-------------------+    +-------------------------------------------------------------------------+
```

Jenkins マシンでは ~/.tool を ~/Box Sync/tool にシンボリックリンクしています

## Box Sync
他のマシンでの更新が sync されてきたところを watchman でフックして git にコミットします

- kms_master_asset は kms/asset とまったく構成になるようにします
- jenkins マシンでは ~/.kms_master_asset/.git -> ~/box/kms_master_asset/.git にシンボリックリンクを張って、直接監視しています
- また ~/box -> ~/Box Sync にシンボリックリンクを張っています
  - スクリプト内ではしばしば正規化されてしまい、

## build.py
自動生成するファイル一式を更新します

パイプラインの詳細については以下を参照してください。

https://confluence.gree-office.net/pages/viewpage.action?pageId=158727563

自動生成対象にはおおまかにいって以下のものがあります
- manifest.json -> Cocos-2d-x AssetMangerEx 用のダウンロードファイルリスト contents/files 以下の更新があったことをクライアントに通知する
- master_data.bin + master_header/*.h -> マスタデータを flatbuffers 化したもの。Excel から生成する

### master-data-xls2json.py
<kms_x_asset>/master/master_data.xlsx を読み込んで、<kms_x_asset>/master_derivatives/master_(schema|data).json を生成します

### json2fbs.py
master-data-xls2json.py で生成した JSON を読み込んで、FlatBuffers スキーマファイル .fbs を生成します

### flatc
.fbs と .json を読み込んで、.bin と .h を生成します

### manifest-generate.py
contents/files 上のファイルから Cocos-2d-x AssetManagerEx 用の project.manifest と version.manifest を生成します

### box-update.py
Box API を使って、手元のデータと Box 上のデータを同期します。
簡易的な Box Sync のようなものです。
Box Web Hook から呼び出されます。

### spine-atlas-update.sh
武器や表情などのテクスチャ置き換えで対応するデータのテクスチャアトラスを TexutrePacker を使って生成します

### sonya.sh
ソーニャちゃんを経由して Chatwork 'KMSビルド' にログを流します。

## watchman

- 監視対象は <kms_x_asset>/contents/files と master/ 以下のみです 
  - watchman/watchman-xxx.json.template を参照してください
- コールバックでは以下のことをします
  - build.py build を実行し、自動生成ファイル一式を更新します
  - ターゲットが master (kms_master_asset) の場合 追加/削除ファイルをチェックして git add/rm します
  - 更新ファイルがあれば git commit + push します
    - コールバックが頻繁に来る/Box Sync での同期に時間がかかるため、watchman-commit.sh で 5 秒遅延させています

watchman については、以下を参照。Docs はわりと親切です。

https://facebook.github.io/watchman/

### watchman-setup.sh
watchman での監視設定をセットアップします。

- 実行すると watchman の watch と trigger 設定をします
  - watchman/watchman-xxx.json.template から watchman/watchman-xxx.json を生成します（パスの置換をします）
- ログは log/watchman-callback.log に出力されます

### watchman-callback.sh
watchman での監視対象に変更があった場合に呼ばれるスクリプトです

- git add/rm をする
- コミットできそうな場合は watchman/watchman-commit.sh に投げる (バックグラウンド)

### watchman-xxx.json.template
watchman trigger で登録する trigger 設定です。

watchman/watchman-setup.sh でパスを置換して使用します

## watchman の停止
pgrep -f watchman で検索して、殺してください

再起動は watchman-setup.sh を実行すれば OK です

# 古いもの

## Box Auth

以下のファイルは現在は使っていません
- box-auth.sh: box にログインし、アクセストークンを git config にセットする
- box-token-refresh.sh: box のアクセストークンをリフレッシュトークンで再取得して、git config にセットする
- box-config.sh: box 設定の共通部分 (source でとりこむ)
- box-backup.sh: リポジトリの mirror を tar で固めたものを box API で upload する (なんかすごい重いです）

## git-media with box
現在は使用していません

- git-media-box-setup.sh: git-media の設定をし、box にログインするスクリプト
- git-media-box-token-refresh.sh: box のトークンを再取得し、git config にセットする

## マスタデータまわり
また、以下は現在は使用していません
- master-data-update.sh
- master-tsv2json.py
