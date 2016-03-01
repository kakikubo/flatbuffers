## KMS Web Hooks
各種の webhook です

KMS AWS 環境の hockeyproxy 上で動作しています

```
$ ssh -t login-kms.gree-dev.net gaws ssh hockeyproxy
```

- Box
- Github Enterprise
- HockeyApp

### デプロイ
./deploy.sh を使いましょう

```
$ ./deploy.sh
```

ローカルマシンから直通で、hockeyapp へアクセスできるようにしておきます
https://confluence.gree-office.net/pages/viewpage.action?pageId=170313456
