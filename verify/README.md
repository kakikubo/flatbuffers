# マスタデータ評価モジュール

## ルート
verify_master_json.py

- テーブル参照チェック
- ファイル参照チェック
- 最大値・最小値チェック（数値）
- 最大長・最小長チェック（数値）
- ラベルチェック
- 必須チェック

## マスタデータの個別のシートごとの評価

### master_data/<シート名>.py を用意してください

小文字開始のファイル名でかまいません。

excel のシート名（= master_data.json のエントリ名）と同じファイル名にしてください。

中身は以下のようにします。

```
#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import codecs
from collections import OrderedDict
from logging import info, debug, warning, error
from base import Base

class enemyPlacement(Base):
    def __init__(self):
        self.table = 'enemyPlacement'

    def verify(self, data, schema = {}, references = {}, file_references = {}, validations = {}):
        group_incidence_map = OrderedDict()
        for d in data:
            group_id = d['groupId']
            if not group_incidence_map.has_key(group_id):
                group_incidence_map[group_id] = 0
            group_incidence_map[group_id] += d['incidence']

        result = True
        for group_id, incidence_total in group_incidence_map.iteritems():
            if not incidence_total in (0, 10000):
                self.error(u".incidence: グループ '%d' の確率の和が 100%% (10000) ではありません: %d" % (group_id, incidence_total))
                result = False

        return result
```

- Base (master_data.base.py) を親クラスにしてください
- self.table には自分のテーブル名をセットしてください
- verify() を用意してください。data 以降の引数は必須でなくしましょう
- verify は True = エラー無し False = エラーありにしてください
- エラーメッセージは self.error か logging.error を使ってその場で出力してしまってかまいません
- メッセージは日本語にし、どの行やどの列に問題があったのか、できるだけ明示するようにしましょう

### master_data/__init.py__ 登録しましょう
追加したファイルを verify_master_json.py から読み込めるように宣言します

```
#!/usr/bin/env python
# coding: utf-8
from master_data.base import Base
from master_data.enemyPlacement import enemyPlacement
 
__author__  = 'kiyoto.suzuki'
__version__ = '0.0.1'
__license__ = 'MIT'
```
