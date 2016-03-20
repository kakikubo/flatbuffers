#使い方

jenkinsユーザで設定ファイル(kms.jenkins.plist)を所定の場所に配置した上で、launchctlに読み込ませます

```
jenkins@asset-jenkins%  cp kms.jenkins.plist ~/Library/LaunchAgents/
jenkins@asset-jenkins%  launchctl load ./Library/LaunchAgents/kms.jenkins.plist
```

サービスが登録されている事、javaのプログラムが稼働していることを確認します

```
g-pc-00363221:~ jenkins$ launchctl list | grep kms.jenkins
67321   0   kms.jenkins
g-pc-00363221:~ jenkins$ ps auxww | grep java
jenkins         39674   0.0  3.9 10296856 648196 s000  S     3:29PM   0:46.46 /usr/bin/java -jar /usr/local/Cellar/jenkins/1.644/libexec/jenkins.war --prefix=/jenkins --httpPort=8080
```

#その他(nginx)

homebrewからインストールしたnginxを以下の通りlaunchctl経由にしています。

```
sudo launctl load /usr/local/Cellar/nginx/1.8.0/homebrew.mxcl.nginx.plist
```

#通常の動作状態

以下の通り、プロセスが立ち上がっていたら問題ないかと思います。

```
g-pc-00363221:jenkins jenkins$ ps auxww | grep ng[i]nx
root            11228   0.0  0.0  2463880   2008   ??  Ss    9:55AM   0:00.01 nginx: master process /usr/local/opt/nginx/bin/nginx -g daemon off;
nobody          11229   0.0  0.0  2500964   1648   ??  S     9:55AM   0:00.07 nginx: worker process
g-pc-00363221:jenkins jenkins$ ps auxww | grep ja[v]a
jenkins         11196   0.0  2.9 10134816 482180   ??  S     9:53AM   0:20.50 /usr/bin/java -jar /usr/local/Cellar/jenkins/1.644/libexec/jenkins.war --prefix=/jenkins --httpPort=8080
```

