# ラズパイ連続撮影システム マニュアル(素案) v3.2.0

## 1. システム概要

タブレット(Termux/Android)からSSH経由でRaspberry Pi(RPi)のカメラを操作し、
サムネイル撮影→動画撮影(任意で音声同時録音)を繰り返す連続撮影システム。

```
[タブレット (Termux)]  --SSH(固定IP)-->  [Raspberry Pi (Bookworm)]
   Androidscripts/                          RPiscripts/
   - connect.sh    (接続・プレビュー)         - script/imageSetting.txt
   - recording.sh  (撮影開始)                 - script/startRecording.py
   - cameraSetting.sh (設定変更)              - script/mjpeg_server.py
   - dataCheck.sh  (データ確認・回収)          - script/preview_start.sh / preview_stop.sh
   - reboot.sh / shutdown.sh
```

### 撮影ループ

1. サムネイル撮影 (`rpicam-jpeg`, 1枚)
2. 動画撮影 (`rpicam-vid`, `video_duration`秒)。音声録音を選択した場合は
   `arecord`でwavを同時録音
3. 1.に戻り、`video_number`回繰り返す(`video_number`は1〜1000、長期運用を
   想定し大きい値を設定する)

### ファイル命名規則

```
{フォルダ名}_{連番4桁}_{タイムスタンプ}.拡張子
```

例: `20260612_クマ_0001_20260612120000.jpg` / `.h264` / `.wav`

- フォルダ名: `{撮影日}_{対象名}` (recording.sh実行時に入力)
- 連番: `0001`〜`9999`
- タイムスタンプ: `YYYYMMDDHHMMSS`
- `.h264`(動画)と`.wav`(音声)は同じ連番・タイムスタンプを持つため、
  PC側でファイル名から対応関係を判別してMP4へ統合できる


## 2. 初期セットアップ(タブレット側)

詳細は `Androidscripts/README.md` を参照。概要のみ記載。

1. Termuxパッケージのインストール: `termux-api`, `jq`, `sshpass`, `openssh`
2. `~/setting/` フォルダを作成し、以下を配置
   - `sshSetting.txt` (SSH認証情報。詳細は6章)
   - `HostTable.csv` (接続先RPiのID・IP対応表)
   - `VERSION` (タブレット側バージョン)
   - `IP.txt` (connect.sh実行時に自動生成。手動編集不要)
3. `.bashrc` に `ssh2raspi()` / `scp2raspi()` 関数を追記(README.md記載のコードをコピー)
4. GitHubリポジトリをzip形式でダウンロードして展開し、`.shortcuts/`
   (タブレット用スクリプト)と `~/RPiscripts/` (RPi用スクリプト、setupRPi.shが使用)
   を配置する(リポジトリにはRPi用スクリプトも同梱されており、タブレット用
   スクリプトの更新と同じ手順でRPi用スクリプトも最新化される。詳細はREADME.md・8章)
   (`sshSetting.txt`・`HostTable.csv`は空のテンプレートなので、初回は記入が必要)

### HostTable.csvの記入例

```csv
host,IP
UT01,192.168.1.101
UT02,192.168.1.102
```

- `host`列は英数字のID(例: `UT01`)。ルーターで各RPiに固定IPを割り当て、
  対応する`IP`列に記入する。
- `connect.sh`実行時、IPが記入された行に対して自動でpingを行い、応答が
  あった機体だけを選択肢として表示する。応答がない場合は手動でID入力する
  画面に切り替わる。


## 3. RPi側セットアップ

`RPiscripts/` の内容をRPiのホームディレクトリに配置する想定
(`~/script/`, `~/record/`, `~/VERSION`)。

### 3.1 カメラ・音声の動作確認

```bash
# サムネイル撮影テスト
rpicam-jpeg -o test.jpg -t 1000 -n

# 動画撮影テスト(imageSettingの値を使う場合は値を直接指定)
rpicam-vid -t 5000 -o test.h264 --width 1920 --height 1080 --framerate 30 --bitrate 8000000

# USBマイクのデバイス名確認
arecord -l
```

`arecord -l`で表示されたデバイス名(例: `plughw:1,0`)を
`script/imageSetting.txt`の`audio_device`に設定する。

### 3.2 imageSetting.txt の項目

| 項目 | 内容 | 範囲 |
|---|---|---|
| width | 動画/サムネイルの幅(px) | 1-2400 |
| height | 動画/サムネイルの高さ(px) | 1-2400 |
| framerate | 動画のフレームレート(fps) | 1-40 |
| bitrate | 動画のビットレート(bps)。`rpicam-vid --bitrate`にそのまま渡す | 100000-25000000 |
| video_duration | 1本あたりの動画の長さ(秒) | 1-3600 |
| video_number | 動画を何本撮影したら終了するか | 1-1000 |
| audio_device | USBマイクのALSAデバイス名 | 文字列(例: plughw:1,0) |

#### bitrateの目安

| 解像度 | フレームレート | bitrate目安 |
|---|---|---|
| 1920x1080 | 30fps | 6,000,000〜10,000,000 (6〜10Mbps) |
| 1280x720 | 30fps | 3,000,000〜5,000,000 (3〜5Mbps) |
| 640x480 | 30fps | 1,000,000〜2,000,000 (1〜2Mbps) |

画質を上げたい場合はbitrateを大きく、ファイルサイズを抑えたい場合は
小さくする。実機で`rpicam-vid`を実行し、ファイルサイズと画質を確認して
調整する。

### 3.3 プレビュー(MJPEGサーバー)

`script/mjpeg_server.py`はpicamera2を使った自作MJPEGストリーミングサーバー。
追加パッケージ不要(picamera2はBookworm標準)。

- 起動: `script/preview_start.sh` (内部で`preview_stop.sh`を呼び一度停止してから起動)
- 停止: `script/preview_stop.sh` (`pkill -f mjpeg_server.py`)
- URL: `http://<RPiのIP>:8080/stream.mjpg`

カメラはlibcamera経由で1プロセスのみが占有できるため、撮影開始前には
必ずプレビューを停止する(`recording.sh`が自動的に行う)。


## 4. 各スクリプトの使い方(タブレット側)

### connect.sh

1. `HostTable.csv`に登録されたIPに対してpingを行い、応答のある機体を
   一覧表示(radioボタン)。応答がない場合は手動でID(例: `UT01`)を入力
2. SSH接続確認
3. SDカード容量チェック(10GB未満の場合は拡張するか確認)
4. プレビューを開始するか確認
5. **現在時刻の確認ポップアップ**: タブレットの現在時刻が表示され、
   「この時刻でRPiの時計を設定してよいか」を確認する。
   - 問題なければ「はい」→ その時刻でRPiの時計を設定
   - 時刻がずれている場合は「いいえ」→ 手動で時刻を入力する画面が表示される
     (`YYYYMMDDHHMMSS`形式、14桁で入力)
6. プレビュー開始、ブラウザで`http://<IP>:8080/stream.mjpg`を表示
7. タブレット側/RPi側それぞれのVERSIONを表示

### recording.sh

1. プレビューを停止(カメラを撮影用に解放)
2. 既に撮影中のプロセスがないか確認(二重起動防止)
3. カメラ起動テスト(`rpicam-jpeg`でテスト撮影)
4. 撮影対象名を入力(フォルダ名 `{撮影日}_{対象名}` の元になる。重複時は
   再入力を求められる)
5. メタデータ(撮影場所・撮影者・対象種等のメモ)を入力 → `memo.txt`に記録
   (RPi_IDも自動で記録される)
6. **音声を同時録音するか確認**(USBマイクが必要)
   - 「はい」→ `.wav`と`.h264`を両方記録
   - 「いいえ」→ `.h264`のみ記録
7. 撮影開始(バックグラウンドで実行され、ウィンドウを閉じても撮影は継続する)

### cameraSetting.sh

`width` / `height` / `framerate` / `bitrate` / `video_duration` /
`video_number` / `audio_device` のいずれかを選択し、値を変更する。
変更前の設定ファイルは`.bak`としてバックアップされる。

### dataCheck.sh

撮影済みフォルダの一覧表示、サムネイル(`.jpg`)のダウンロード、
撮影データの削除(2段階確認)。

### reboot.sh / shutdown.sh

RPiの再起動・シャットダウン。


## 5. PC側でのMP4統合について

撮影後、`record/{フォルダ}/`内の`.h264`(動画)と`.wav`(音声)はファイル名
(連番・タイムスタンプ)で対応しているため、PC側で同じ連番・タイムスタンプ
のペアを探してMP4に統合する。

例: `20260612_クマ_0001_20260612120000.h264` と
    `20260612_クマ_0001_20260612120000.wav` → 同じMP4に統合

音声を録音しなかった場合、対応する`.wav`は存在しない(`.h264`のみ)。


## 6. 認証情報(SSHユーザー名・パスワード)の変更手順

SSH認証情報は `setting/sshSetting.txt` の1か所のみで管理している。

```
user=(ユーザー名)
pass=(パスワード)
```

`.bashrc`の`ssh2raspi()`関数がこのファイルを毎回sourceして読み込むため、
**他のスクリプトを書き換える必要はない**。

変更手順:

1. タブレット側: `setting/sshSetting.txt` の `user=` / `pass=` を編集する
2. RPi側: 対応するLinuxユーザーのパスワードを `passwd` コマンドで変更し、
   1.で設定した値と一致させる

複数のRPiで同じ認証情報を共有運用している場合は、**全てのRPiで手順2を
実施**しないと、一部の機体に接続できなくなるので注意すること。


## 7. トラブルシューティング

| 症状 | 確認・対処 |
|---|---|
| connect.shで機体が一覧に出てこない | `HostTable.csv`のIPが正しいか、RPiの電源・Wi-Fi接続を確認。pingが通らない場合は手動入力でIDを入力 |
| SSH接続に失敗する | `setting/sshSetting.txt`の認証情報、RPi側のパスワードが一致しているか確認(6章) |
| プレビューが表示されない | RPi側で`script/preview_start.sh`が起動しているか確認。`pkill -f mjpeg_server.py`後に再実行 |
| 撮影開始直後に失敗する/カメラが掴めない | プレビューが残っていないか確認(`preview_stop.sh`実行)。カメラは1プロセスのみが排他利用可能 |
| 「既に撮影中です」と表示される | `record/.recording.pid`が残っている可能性。実際に撮影中でない場合はRPi上で削除する |
| 音声が記録されない | `arecord -l`でUSBマイクが認識されているか、`imageSetting.txt`の`audio_device`が正しいか確認 |
| RPiの時刻がずれている | connect.sh実行時の時刻確認ポップアップで「いいえ」を選び、正しい時刻を手動入力する |
| SDカード容量が10GB未満と表示される | connect.shの確認ダイアログで「はい」を選ぶとストレージ拡張+再起動を実行 |
| setupRPi.shで「~/RPiscripts/script が見つかりません」と表示される | リポジトリのzipを展開していない(2章・8.1節参照) |
| setupRPi.shのパッケージインストールが失敗する | RPi上のユーザーがパスワード無しで`sudo`を実行できるか確認(8.4節) |


## 8. RPiスクリプトのセットアップ・更新(setupRPi.sh)

RPi側の`script/`フォルダ(`imageSetting.txt`を除く)とパッケージインストールを、
タブレットからSSH経由でまとめて実行できる。

### 8.1 準備(タブレット側)

RPi用スクリプトは、タブレット用スクリプトと同じGitHubリポジトリに同梱されている
(リポジトリ直下の`RPiscripts/`フォルダ)。2章のセットアップ/更新手順を
実行すると、`~/RPiscripts/VERSION`と`~/RPiscripts/script/*`が自動的に
配置・更新される。個別に別リポジトリ・別zipを取得する必要はない。

### 8.2 setupRPi.shの実行

1. 接続先RPiを選択(connect.shと同様、ping検出+選択 or 手動入力)
2. SSH接続確認
3. 実行内容を選択
   - **初期セットアップ(パッケージインストール含む)**: 新規RPi向け。
     `script/`フォルダの転送、`record/`フォルダ作成、必要パッケージ
     (`python3-picamera2`, `rpicam-apps`, `alsa-utils`)のインストールを行う
   - **スクリプト更新のみ**: 既存RPi向け。`script/`フォルダの転送のみ行う
4. `script/`フォルダをRPiの`~/script`へ転送(`scp`)

### 8.3 imageSetting.txtの扱い

RPi側に既に`script/imageSetting.txt`が存在する場合は、転送後に元の内容へ
復元する。そのため、機体ごとに調整したwidth/bitrate等の設定は上書きされない。
新規セットアップ時(ファイルが存在しない場合)のみ、転送したデフォルト値の
`imageSetting.txt`がそのまま使われる。

### 8.4 注意点

- パッケージインストールはRPi上のユーザーがパスワード無しで`sudo`を実行
  できることを前提にしている(Raspberry Pi OSのデフォルト設定)
- `scp`はコピー先の不要ファイルを削除しないため、`script/`内のファイルを
  削除・リネームした場合はRPi側で手動削除が必要


## 9. VERSION管理

タブレット側(`setting/VERSION`)・RPi側(`~/VERSION`)それぞれにバージョン
文字列(例: `v3.0.0`)を配置している。`connect.sh`実行時に両方を表示するので、
更新漏れがないか確認できる(自動での整合性チェック・強制は行わない)。


## 10. Web UI (v4)の`/system`ページについて

v4(RPi上で常時稼働するFlask Webアプリ、`RPiscripts/webapp/`)では、
ブラウザで`http://<RPiのIP>:8080/system`にアクセスすることで、
本章で説明する操作が行える。セットアップ自体は`RPiscripts/webapp/README.md`
を参照。

### 10.1 提供機能

| 機能 | 内容 | 撮影中の制限 |
|---|---|---|
| カメラプロセスのリセット | `rpicam-vid`/`rpicam-jpeg`/`arecord`を強制終了。プレビューが「カメラの初期化に失敗しました」になる場合の復旧手段 | 使用不可 |
| 再起動 | 1分後にRPiを再起動。systemd自動起動(後述)が設定済みならwebappも自動復帰する | 使用不可 |
| シャットダウン | 1分後にRPiをシャットダウン(完全に電源OFF)。**再度使うには物理的に電源を入れ直す必要がある**(リモートでの再起動は不可) | 使用不可 |
| 予約をキャンセル | 再起動・シャットダウンの予約を取り消す(`shutdown -c`) | 制限なし |
| 時刻設定(端末の時刻) | この端末(ブラウザ)の現在時刻でRPiの時計を設定 | 使用不可 |
| 時刻設定(手動入力) | 年/月/日/時/分/秒を個別入力してRPiの時計を設定。端末の時刻が正しくない場合のフォールバック | 使用不可 |

シャットダウンは、観察終了後にバッテリー消費を抑えて機体を回収する場合などに
使う想定。誤操作防止のため各操作には確認ダイアログがあり、再起動・
シャットダウンは1分の遅延後に実行されるため、その間は「予約をキャンセル」で
取り消せる。

### 10.2 セットアップ時の注意(NOPASSWD設定)

再起動・シャットダウン・時刻設定は内部で`sudo shutdown`/`sudo date`を実行する。
デフォルトユーザー`pi`であれば追加設定不要だが、それ以外のユーザーで運用する
場合は、`sudo visudo -f /etc/sudoers.d/rpi-webapp`で以下の1行を追加する
(`<user>`は実際のユーザー名)。

```
<user> ALL=(ALL) NOPASSWD: /usr/sbin/shutdown, /usr/bin/date
```

**これを設定していないと、SSHで直近に`sudo`を使った直後の数分間だけ
ボタンが正常に動作し、それ以外のタイミングでは「実行しました」という
表示が出るのに実際には何も起きない**、という分かりにくい不具合になるため
注意。設定後は`sudo -n shutdown -h +1 && echo OK`(成功後`sudo -n shutdown -c`で
キャンセル)でパスワード無しで実行できることを確認する。

### 10.3 トラブルシューティング(v4追加分)

| 症状 | 確認・対処 |
|---|---|
| `/system`の再起動・シャットダウン・時刻設定で「実行しました」と表示されるが何も起きない | 10.2のNOPASSWD設定が未済の可能性。`sudo journalctl -u rpi-webapp.service -n 10 --no-pager`で`sudo: a password is required`が出ていないか確認 |
| シャットダウン後、RPiにアクセスできなくなった | 想定通りの動作。物理的に電源を入れ直す(USB電源の抜き差し等) |
| 再起動後、ブラウザでwebappにアクセスできない | `RPiscripts/webapp/rpi-webapp.service`がsystemdに登録・有効化されているか確認(`sudo systemctl status rpi-webapp.service`) |
