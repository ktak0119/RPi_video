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
   RPi上の実際のユーザー名・clone先パスに合わせて編集する。
   デフォルトでは`User=pi`・`/home/pi/...`としているので、ユーザー名が
   異なる場合は両方を実際のユーザー名(例: `ktak`なら`/home/ktak/...`)に
   書き換えること
   (`%h`は使わず、ホームディレクトリの絶対パスを書くこと。
   systemdのシステムサービスでは`%h`は常に`/root`に展開されるため)
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

## 「システム」ページの再起動・シャットダウン・時刻設定について

これらは`sudo`で`shutdown`/`date`コマンドを実行する。Raspberry Pi OSの
デフォルトユーザー`pi`であれば`sudo`がパスワード無しで使えるため追加設定は
不要だが、それ以外のユーザーで運用する場合は**NOPASSWDの設定が必須**。

設定していない場合、SSHで直近にsudoを使っていればその認証キャッシュ
(デフォルト約15分)で動いてしまうため、一見動作するように見えても、
キャッシュが切れるとボタンを押しても画面上は成功表示のまま実際には
何も実行されない(`sudo: a password is required`がjournalctlに記録される)。

以下を実行して専用のsudoers設定を追加する(`<user>`は実際のユーザー名に置き換え):

```
sudo visudo -f /etc/sudoers.d/rpi-webapp
```

エディタが開いたら以下の1行を追加して保存:

```
<user> ALL=(ALL) NOPASSWD: /usr/sbin/shutdown, /usr/bin/date
```

設定後、`sudo -n shutdown -h +1 && sudo shutdown -c`でパスワード無しで
実行できるか確認できる(`sudo -n`はパスワード入力が必要な場合エラーになる)。
