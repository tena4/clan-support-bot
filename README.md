# clan-support-bot

プリコネR用のクランバトル支援bot

## 導入(heroku)

discord botアカウントやherokuの準備は出来ている前提

1. herokuアプリの作成と設定
```
heroku app clan-support-bot
heroku stack:set container -a clan-support-bot
```

2. herokuアプリの環境変数を設定
```
heroku config:set BOT_TOKEN=<discord_bot_token>
```

3. heroku用gitリモートの追加(プロジェクトディレクトリ下で実行)
```
heroku git:remote -a clan-support-bot
```

4. herokuへデプロイ
```
git push heroku master
```

5. herokuアプリの起動
```
heroku ps:scale worker=1
```
