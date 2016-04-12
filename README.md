# Toybox tool リポジトリ

Asset パイプライン用のスクリプトなどをおいています

ビルド用の Jenkins マシンや開発用の PHP サーバで動くものがメインになります

# jenkins マシンでの差分監視と自動コミット
以下のような構成で、box sync にファイルを投げ込むと、数秒後に自動で gitlab の (kms|argo)/asset が更新されます

```
master
 each user                jenkins (Jenkins Mac Book)                                    git (Gree GHE)
 +--------------------------+    +--------------------------------------------------------------+    +------------------+
 | Box Sync                 | -> | Box Sync                -> jenkins -> build.py -> git commit | -> | Github           |
 | (kms|argo)_master_asset  |    | (kms|argo)_master_asset   (watchman)              git push   |    | (kms|argo)/asset |
 +--------------------------+    +--------------------------------------------------------------+    +------------------+

personal working
 each user                jenkins (Jenkins Mac Book)
 +--------------------------+    +--------------------------------------------------------------------------------------------------------------+
 | Box Sync                 | -> | Box Sync                             -> jenkins -> build.py -> /var/www/cdn/xxx.yyy                          |
 | (kms|argo)_xxx.yyy_asset |    | (kms|argo)_xxx.yyy_asset  (watchman)                           http://(kms|argo)-dev.dev.gree.jp/cdn/xxx.yyy |
 +--------------------------+    +--------------------------------------------------------------------------------------------------------------+
```

以前は watchman に ~/Box Sync 以下を監視させて、変更をフックして build.py (watchman-build.sh) を起動していましたが、
イベントが多すぎて jekins のジョブキューがつまるため、現在は明示的に jenkins からキックしてもらう運用になっています

## ディレクトリ設計

### このリポジトリの動作環境
~/toybox/tool 以下にチェックアウトして使うことを想定しています。

いちおう他の場所に置いても動作するように作っているつもりです。

### Box Sync 
Jenkins マシンでは ~/Box Sync を ~/box にシンボリックリンクしています

### git asset repository
~/(kms|argo)/asset 以下にチェックアウトして使うことを想定しています

これは build.py --git-dir で指定し、変えることができます

git の commit と push 自体を build.py が行うことはありません。
build.py の完了後に watchman-build.sh から呼び出される watchman-commit.sh で commit と push が行われます

### ビルド時のワーキングとミラー
build.py は、実行に時間がかかるため、その間に Box Sync 経由でのファイル更新が入ってしまい、
どの時点のアセットでビルドされたものか、正確にわからなくなってしまうことがあります

これを防ぐために、build.py は実行の開始時に rsync で、対象の Box Sync ディレクトリのミラーを生成し、そこ以下のファイルを入力として用います

また、build.py 中で生成されたファイルは一時的にワーキングディレクトリ以下に置かれ、
ビルドステップの最後で、Box Sync 以下および上記ミラーへとインストールされ、
その後、CDN や git リポジトリに rsync されます

これは build.py の --build-dir --mirror-dir で変えることができます

### リモート CDN
build.py は、生成したアセットを実機から参照するために、S3 経由でのアップロードを行います

アップロードされる内容は、基本的には asset/contents 以下のすべてと、管理用の manifest ファイルから成っています

細かい構成は、要件によって微妙に変えていっていますので、実際に動かしてみて、内容を確認するのがもっともてっとりばやいと思います

### ローカル CDN
build.py は、生成したアセットの確認用として、ローカル PC 上の CDN 領域（公開領域）への配布を行います

配布される内容は、リモート CDN と同様のものです

このローカル CDN は  nginx ないし apache 経由でアクセスされることを想定しています
ローカル CDN のデフォルトは /var/www/cdn ですが、build.py からは --cdn-dir の指定で切り替えることができます

#### ローカル CDN の経緯
当初は、実際に開発中のアセットはこちらから取得するつもりでしたが、
S3 ないし akamai の料金が非情に安いため、開発用のアセットもきちんとした CDN に配置するようにしています

こうすることで、開発中から本番と同等のネットワーク構成で運用することができ、障害点を減らすことができます

## セットアップ
Asset パイプラインは python がメインで、サブで bash を用いています
python は pip 経由でインストールし、必要なコマンドラインツールは brew でインストールしていきます

```
$ git submodule update --init --recursive
$ easy_install pip
$ sudo pip install -r requirements.txt
$ brew install jq imagemagick awscli
```

### flatbuffers
flatbuffers のツール flatc をビルドします

```
$ brew install cmake
$ cd flatbuffers
$ cmake .
$ make
```

## build.py
自動生成するファイル一式を更新します

### デバッグの仕方
手元の PC でもデバッグすることができます。

(kms_master_asset をビルドする場合は以下のようにします

```
$ git clone git@git.gree-dev.net:toybox/tool.git
$ cd tool
$ cp -rp ~/Box\ Sync/kms_master_asset kms_master_asset
$ ./script/build.py debug master
```

個人アセットの場合は、次のようになります

```
$ git clone git@git.gree-dev.net:toybox/tool.git
$ cd tool
$ cp -rp ~/Box\ Sync/kms_master_asset kms_master_asset
$ cp -rp ~/Box\ Sync/kms_kiyoto.suzuki_asset kms_kiyoto.suzuki_asset
$ ./script/build.py debug kiyoto.suzuki
```

debug と build の違いは、更新されたアセットを S3 やローカルの CDN 上にコピーするか否かの違いです
(つまり --cnd-dir --git-dir 等が無効になります）

--log-level DEBUG オプションをつけるとすこし出力が増えます
（実際のところはほぼすべて INFO レベルで出力しているため）

## 有料ツール

以下のツールは有料ですので、すべての機能を手元で動作させるには、マシンごとにライセンスを購入する必要があります

- TexturePacker
- GlyphDesigner
- Imesta (build.py から必要ではない）

いちおうなくてもビルドが動作 (ツールが必用な箇所をスキップ）するように作っていますが、
メンテナンス不足で、動かなくなっていることがあるかもしれません

## すこし古いドキュメント
パイプラインの設計については以下を参照してください。

https://confluence.gree-office.net/pages/viewpage.action?pageId=158727563

