# Neo4j Multi Server and Database
Neo4j のマルチサーバ + データベース設定を作成するためのスクリプトです

- Neo4j のパッケージに入っている起動スクリプトの対応が不完全なため、コピーして少しいじってあります (NEO4J_HOME を環境変数で設定できるようにしてある）
- マルチサーバルートディレクトリ ~/neo4j (環境変数 NEO4J_MULTI_ROOT で指定できます）
- Neo4j インストールディレクトリ (brew で入れた /usr/local/Cellar/neo4j/x.y.z を想定しています）
- 設定の出力には jinja2 テンプレートを使っています

## 使い方
ユーザ名とポートを指定します。

```
 $ ./neo4j-multi-setup.sh kiyoto.suzuki 7600

```

これで、 ~/neo4j/kiyoto.suzuki 以下に port 7600 でアクセスできる Neo4j サーバインスタンスが立ち上がる設定が出力されます

###　全ユーザに設定して回る
~/box/kms_master_asset/manifests/dev.asset_list を使います

```
 $ ./neo4j-multi-setup-all.sh 
```

port は配列のインデックス * 10 で決定されます

## サーバの起動
環境変数 NEO4J_HOME をそれぞれのユーザのディレクトリに指定して起動します

```
 $ NEO4J_HOME=~/neo4j/kiyoto.suzuki ./neo4j start
 Starting Neo4j Server...WARNING: not changing user
 process [63608]... waiting for server to be ready...... OK.
 http://localhost:7600/ is ready.
```

### 全ユーザを起動して回る
~/box/kms_master_asset/manifests/dev.asset_list のユーザすべてにコマンドを実行します

```
 $ ./neo4j-all.sh start
```
