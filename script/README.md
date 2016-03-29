
## アセットビルドスクリプト
アセットのビルドは、様々なスクリプトの統合です

基本的に build.py から呼ぶスクリプトのみを置くようにしてください

それ以外のスクリプトは別のサブディレクトリに置くようにしましょう

## 新しい Python のスクリプトを追加する

### IO のファイル/ディレクトリをできるだけ明確にしましょう
ひとつひとつはシンプルなツールにして、
中間ファイルをできるだけ box や git に置くようにするとデバッグがしやすくなります

### きちんとアプリケーションクラスを作りましょう

```
class ToolName():
    def __init__(self):
        self.hoge = True
        ...
```

### argparse を使うようにしましょう

```
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='something for description', epilog="""\
example:
    $ ./tool_name.py arg1""")

    parser.add_argument('arg1', help='input argument 1')
    ...
```

### logging を使うようにしましょう

--log-level というオプションをつけて WARNING INFO DEBUG などを受け入れるべきです

```
import logging
from logging import info, warning, debug


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='something for description')
    parser.add_argument('--log-level', help = 'log level (WARNING|INFO|DEBUG). default: INFO')

    args = parser.parse_args()
    logging.basicConfig(level = args.log_level or "INFO", format = '%(asctime)-15s %(process)d %(levelname)s %(message)s')
```

### エラーメッセージは日本語で出しましょう
残念ながら Exception には unicode を用いることができないため、error で出力して、その後同じ内容で Exception しましょう

```
    error = hoge()
    if error:
        error("エラーがありましたよー: {error}".format(error = error))
        throw Exception("some errors occurred") 

```

### build.py から呼び出しましょう

__init__ 内で、追加するツールに必要な定数を切りましょう

```
    def __init__(self, ...):
        ...
        self.tool_name_dir = self.org_main_dir+'/tool_name'
        ...
        self.org_tool_name_dir = self.org_main_dir+'/tool_name'
        ...
        self.master_tool_name_dir = self.master_dir+'/tool_name'
        ...
        self.tool_name_bin = self_dir+'/tool_name.py'
        ...
        self.TOOL_NAME_FILE = "tool_name.json"
```

build() 内の適切な箇所で呼び出すようにします

- 呼び出すメソッドは build_xxx() にします
- 引数はできるだけメソッドの引数化するようにしましょう （冒頭でデフォルト設定を補完します）
- 実際に呼び出す前にコマンドラインを info でログに吐きましょう。デバッグ時に利用できますし、エラー時に落ちた場所がわかりやすくなります
- 出力先は、いったん build_dir 以下に出力するようにします

```
    def build_tool_name(self, input1=None, output1=None):
        input1 = input1 or None
        output1 = input1 or self.build_dir+'/'+self.TOOL_NAME_FILE

        cmdline = [self.tool_name_bin, input1, output1]
        info(' '.join(cmdline))
        check_call(cmdline)
        return True

    ...
    def build(self):
        ...
        self.build_tool_name()
        ...
```

build_xxx() で作成したファイルをインストール（コピー）しましょう

```
    def install_generated(self, build_dir=None):
        build_dir = build_dir or self.build_dir
        # fixed pathes
        list = [
            (self.MASTER_JSON_SCHEMA_FILE,        self.master_schema_dir, self.org_master_schema_dir),
            ...
            (self.TOOL_NAME_FILE,                 self.tool_name_dir,     self.org_tool_name_dir),
        ...
```

CDN への配布は main_dir 以下の contents がすべて配られるイメージです


#### 個人アセットにも対応しましょう
わりと忘れがちなので、作成時にテストするのを忘れないようにしましょう

- self.main_dir: 個人アセットディレクトリ (master の場合は master_dir と同一)
- self.org_main_dir: 個人アセットディレクトリのミラー元 (~/Box Sync/kms_xxx.yyy_asset)
- self.master_dir: マスタアセットディレクトリ (kms_master_asset のミラー)
- self.master_dir: ~/Box Sync/kms_master_asset
