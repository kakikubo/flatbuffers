## Deprecated

### box-update.py
Box API を使って、手元のデータと Box 上のデータを同期します。
簡易的な Box Sync のようなものです。
Box Web Hook から呼び出されます。

### Box Auth

以下のファイルは現在は使っていません
- box-auth.sh: box にログインし、アクセストークンを git config にセットする
- box-token-refresh.sh: box のアクセストークンをリフレッシュトークンで再取得して、git config にセットする
- box-config.sh: box 設定の共通部分 (source でとりこむ)
- box-backup.sh: リポジトリの mirror を tar で固めたものを box API で upload する (なんかすごい重いです）

### git-media with box
現在は使用していません

- git-media-box-setup.sh: git-media の設定をし、box にログインするスクリプト
- git-media-box-token-refresh.sh: box のトークンを再取得し、git config にセットする
