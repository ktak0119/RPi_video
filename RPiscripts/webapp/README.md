# RPi連続撮影 Web UI (v4)

RPi上で常時稼働するFlask Webアプリ。タブレットのブラウザから
`http://<RPiのIP>:8080/` にアクセスして操作する。

## 手動起動・デバッグ用

```
./start_webapp.sh   # 起動(既存プロセスがあれば停止してから起動)
./stop_webapp.sh    # 停止
```

## systemdによる自動起動

再起動・シャットダウンをブラウザの「システム」ページから行う場合、
再起動後にこのwebappが自動起動するようsystemdへ登録しておく。

1. `rpi-webapp.service`内の`User=`・`WorkingDirectory`・`ExecStart`を、
   RPi上の実際のユーザー名・clone先パスに合わせて編集する
2. サービスを登録・有効化する

   ```
   sudo cp rpi-webapp.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now rpi-webapp.service
   ```

3. 以後の起動・停止・再起動はsystemctl経由で行う
   (`start_webapp.sh`/`stop_webapp.sh`は使わない)

   ```
   sudo systemctl restart rpi-webapp.service
   sudo systemctl stop rpi-webapp.service
   sudo systemctl status rpi-webapp.service
   ```

※「システム」ページの再起動・シャットダウン・時刻設定は`sudo`で
  `shutdown`/`date`コマンドを実行する。Raspberry Pi OSのデフォルト設定
  (piユーザーがパスワード無しでsudo実行可能)であれば追加設定は不要。
