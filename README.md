# RPi連続撮影 Web UI (v4)

> [!WARNING]
> **本リポジトリは開発中のベータ版です。**
> ソフトウェア、ハードウェア構成、部品表、マニュアルは今後変更される可能性があります。

Raspberry Piを用いた野外動画記録システムのための
オープンソースソフトウェアおよびオープンなハードウェア構成ドキュメントを提供します。

- **ソフトウェア**: RPi上で常時稼働するFlask Webアプリ。タブレットのブラウザから
  `http://<RPiのIP>:8080/` にアクセスして操作する。
- **ハードウェア**: 部品表・配線図・組み立て手順・筐体加工情報・3Dプリントデータ等を
  [`hardware/`](hardware/) に収録。

## 参考文献

本システムのアイデアは以下の論文に基づいています:

> Droissart, V., Azandi, L., Onguene, E. R., Savignac, M., Smith, T. B., & Deblauwe, V. (2021).
> PICT: A low-cost, modular, open-source camera trap system to study plant–insect interactions.
> *Methods in Ecology and Evolution*, 12(8), 1389–1396.
> https://doi.org/10.1111/2041-210X.13618

## ライセンス

| 対象 | ライセンス |
|------|-----------|
| ソフトウェア (`.py`, `.sh`, `.html` 等) | [MIT](LICENSE) |
| ハードウェア資料 (`hardware/` 以下) | [CC BY 4.0](hardware/LICENSE) |

## 手動起動・デバッグ用

```
./start_webapp.sh   # 起動(既存プロセスがあれば停止してから起動)
./stop_webapp.sh    # 停止
```

## systemdによる自動起動

再起動・シャットダウンをブラウザの「システム」ページから行う場合、
再起動後にこのwebappが自動起動するようsystemdへ登録しておく。

1. まず**未編集のまま**`/etc/systemd/system/`へコピーする
   (リポジトリ内の`rpi-webapp.service`は編集しない。編集すると以後の
   `git pull`でこのファイルがコンフリクトする)

   ```
   sudo cp rpi-webapp.service /etc/systemd/system/
   ```

2. コピー先(`/etc/systemd/system/rpi-webapp.service`)を、RPi上の実際の
   ユーザー名・clone先パスに合わせて編集する

   ```
   sudo nano /etc/systemd/system/rpi-webapp.service
   ```

   デフォルトは`User=pi`・`/home/pi/...`。ユーザー名が異なる場合は
   `User=`と`WorkingDirectory`/`ExecStart`内のパスを両方、実際のユーザー名
   (例: `alice`なら`/home/alice/...`)に書き換えること
   (`%h`は使わず、ホームディレクトリの絶対パスを書くこと。
   systemdのシステムサービスでは`%h`は常に`/root`に展開されるため)

3. 登録・有効化する

   ```
   sudo systemctl daemon-reload
   sudo systemctl enable --now rpi-webapp.service
   ```

4. 以後の起動・停止・再起動はsystemctl経由で行う
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

- nanoの場合: `Ctrl+O` → `Enter`(保存) → `Ctrl+X`(終了)
- viの場合: `Esc` → `:wq` → `Enter`
- `visudo`は保存時に文法チェックを行うので、エラーが出た場合は指示に従って修正する

設定後、`sudo -n shutdown -h +1 && echo OK`でパスワード無しで実行できるか
確認できる(`sudo -n`はパスワード入力が必要な場合エラーになる)。`OK`が
表示されたらすぐに`sudo -n shutdown -c`でキャンセルする。

webapp経由で再起動・シャットダウン・時刻設定を試した後、
`sudo journalctl -u rpi-webapp.service -n 10 --no-pager`で
`sudo: a password is required`等のエラーが出ていないか確認する。
