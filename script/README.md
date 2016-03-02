
## アセットビルドスクリプト
アセットのビルドは、様々なスクリプトの統合です
次のようなスクリプトからなりなっています

### master_data_xls2json.py
<kms_x_asset>/master/master_data.xlsx を読み込んで、<kms_x_asset>/master_derivatives/master_(schema|data).json を生成します

### json2fbs.py
master-data-xls2json.py で生成した JSON を読み込んで、FlatBuffers スキーマファイル .fbs を生成します

### flatc
.fbs と .json を読み込んで、.bin と .h を生成します

### manifest_generate.py
contents/files 上のファイルから Cocos-2d-x AssetManagerEx 用の project.manifest と version.manifest を生成します

### make_bitmap_font.py
Glyph Desinger というツールを使って、表示に必要なビットマップフォントを生成します。
- フォント化対象の文字種はマスタデータの特定のシートおよび列を font にて指定します
- 固定でフォントに含めるものについては fontChars シートに記述してあります
- lua スクリプトからも文字を取得します
- ビットマップフォントの設定は asset の glyph_designer 以下から取得します
  - ファイル名とフォント名を一致させる必要があります
  - フォント種別を任意で追加することができます

### sonya.sh
ソーニャちゃんを経由して Chatwork 'KMSビルド' にログを流します。
タイトルとメッセージに使うログファイル名、リファレンスのリンク用 URL を指定できます


