# KMS tool リポジトリ

Asset パイプライン用のスクリプトなどをおいています

ビルド用の Jenkins マシンや開発用の PHP サーバで動くものがメインになります

# jenkins マシンでの差分監視と自動コミット
以下のような構成で、box sync にファイルを投げ込むと、数秒後に自動で gitlab の kms/asset が更新されます

```
master
 each user                jenkins (Jenkins Mac Book)                                    git (Gree GHE)
 +-------------------+    +--------------------------------------------------------+    +-----------+
 | Box Sync          | -> | Box Sync         -> watchman -> build.py -> git commit | -> | Github    |
 | kms_master_asset  |    | kms_master_asset                            git push   |    | kms/asset |
 +-------------------+    +--------------------------------------------------------+    +-----------+

working
 each user                jenkins (Jenkins Mac Book)
 +-------------------+    +------------------------------------------------------------------------------------+
 | Box Sync          | -> | Box Sync         -> watchman -> build.py -> /var/www/cdn/xxx.yyy                   |
 | kms_xxx.yyy_asset |    | kms_xxx.yyy_asset                           http://kms-dev.dev.gree.jp/cdn/xxx.yyy |
 +-------------------+    +------------------------------------------------------------------------------------+
```

Jenkins マシンでは ~/.tool を ~/Box Sync/tool にシンボリックリンクしています

## Box Sync
他のマシンでの更新が sync されてきたところを watchman でフックして git にコミットします

- kms_master_asset は kms/asset とまったく構成になるようにします
- jenkins マシンでは ~/.kms_master_asset/.git -> ~/box/kms_master_asset/.git にシンボリックリンクを張って、直接監視しています
- また ~/box -> ~/Box Sync にシンボリックリンクを張っています
  - スクリプト内ではしばしば正規化されてしまい、いろいろ面倒なので作りました

## build.py
自動生成するファイル一式を更新します

### デバッグの仕方
手元の PC でもデバッグすることができます。

kms_master_asset をビルドする場合は以下のようにします

```
$ git clone git@git.gree-dev.net:kms/tool.git
$ cd tool
$ cp -rp ~/Box\ Sync/kms_master_asset kms_master_asset
$ ./script/build.py debug master
```

個人アセットの場合は、次のようになります

```
$ git clone git@git.gree-dev.net:kms/tool.git
$ cd tool
$ cp -rp ~/Box\ Sync/kms_master_asset kms_master_asset
$ cp -rp ~/Box\ Sync/kms_kiyoto.suzuki_asset kms_kiyoto.suzuki_asset
$ ./script/build.py debug kiyoto.suzuki
```

debug と build の違いは、更新されたアセットを S3 やローカルの CDN 上にコピーするか否かの違いです

#### python のセットアップ
python のモジュールがいろいろ必要ですが、頑張っていれていきましょう

```
$ easy_install pip
$ sudo pip install xlrd
$ sudo pip install pillow
$ brew install jq
```

#### すこし古いドキュメント
パイプラインの詳細については以下を参照してください。

https://confluence.gree-office.net/pages/viewpage.action?pageId=158727563

自動生成対象にはおおまかにいって以下のものがあります
- manifest.json -> Cocos-2d-x AssetMangerEx 用のダウンロードファイルリスト contents/files 以下の更新があったことをクライアントに通知する
- master_data.bin + master_header/*.h -> マスタデータを flatbuffers 化したもの。Excel から生成する
- rsync を使って box のアセットを cdn 用のディレクトリにコピーする

