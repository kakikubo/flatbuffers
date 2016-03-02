#使い方

jenkinsユーザで以下の設定ファイルをlaunchctlに読み込ませます

```
jenkins@asset-jenkins%  launchctl load ./kms/tool/jenkins/kms.jenkins.plist
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


