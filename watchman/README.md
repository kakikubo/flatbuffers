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
  - watchman/template/watchman-xxx.json.template から watchman/template/watchman-xxx.json を生成します（パスの置換をします）
- ログは log/watchman-callback.log に出力されます

### watchman-setup-all.sh
watchman-setup.sh をすべての ~/box/kms_*_asset に対して呼び出します

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

## watchman のサービス化
デフォルトでは /Library/LaunchAgent/ 以下に com.github.facebook.watchman.plist が入っています。

