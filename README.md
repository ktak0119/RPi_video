# RPi連続撮影システム タブレット側スクリプト

Termux(Android)からSSH経由でRaspberry Piのカメラを操作し、連続動画撮影
(サムネイル + 動画、任意で音声同時録音)を行うためのスクリプト集。

タブレット側・RPi側それぞれにVERSIONファイルを同梱している。`connect.sh`
実行時に両者のVERSIONを表示するので、バージョンが一致しているか確認できる。

このリポジトリはタブレットに配置するスクリプト一式(本ディレクトリ)と、
RPiに配置するスクリプト一式(`RPiscripts/`)をまとめて配布するためのもの。
取得・配置方法は「スクリプトの取得・アップデート」を参照。


## タブレットのセットアップ

```
#storageへのアクセスの有効化
termux-setup-storage

#.shortcutsフォルダの生成と有効化
mkdir .shortcuts
chmod 700 -R .shortcuts

#settingフォルダの生成と有効化
mkdir setting
chmod 700 -R setting

#パッケージのインストール
pkg up
pkg install termux-api
pkg install jq
pkg install sshpass
pkg install openssh

#※python3は旧IPsearch.py用にインストールしていたが、IP検索機能の廃止により不要になった
#※iproute2(ip neigh)も旧IPsearch.sh専用だったため不要になった

#pingコマンドが使えるか確認(connect.shの接続先検出に使用)
ping -c 1 1.1.1.1

#上記コマンドでエラーになる場合は以下を試す
#pkg install inetutils

#.bashrcへの書き込み
function ssh2raspi() {
    source ~/setting/sshSetting.txt
    command sshpass -p "$pass" ssh -p 22 -o StrictHostKeyChecking=no $user@$1 $2 $3
}

function scp2raspi() {
    source ~/setting/sshSetting.txt
    command sshpass -p "$pass" scp -r -o StrictHostKeyChecking=no -P 22 "$@"
}
```


## スクリプトの取得・アップデート(タブレット側 + RPi用スクリプトの取得)

このリポジトリをzip形式でダウンロードして展開し、所定の位置に配置する。
**初回セットアップ・以降の更新ともに同じ手順**で行う。

### 1. ダウンロード

ブラウザでこのリポジトリのページを開き `Code → Download ZIP` を選択するか、
Termuxで以下を実行する。

```
curl -L -o storage/downloads/repo.zip \
  https://github.com/ktak0119/RPi_video/archive/refs/heads/main.zip
```

リポジトリ直下の構成は以下の通り。

```
(リポジトリのルート = ダウンロードしたzipを展開した RPi_video-main/ の内容)
├── connect.sh
├── setupRPi.sh
├── recording.sh
├── cameraSetting.sh
├── dataCheck.sh
├── reboot.sh
├── shutdown.sh
├── HostTable.csv        (テンプレート。IP列は空)
├── sshSetting.txt        (テンプレート。user=/pass= は空)
├── IP.txt                 (空。connect.sh実行時に自動生成)
├── VERSION              (タブレット側スクリプトのVERSION)
├── README.md
├── manual/
│   └── manual_draft.md
└── RPiscripts/
    ├── VERSION          (RPi側スクリプトのVERSION)
    └── script/
        ├── imageSetting.txt
        ├── common.py
        ├── startRecording.py
        ├── mjpeg_server.py
        ├── preview_start.sh
        └── preview_stop.sh
```

### 2. 展開・配置

GitHubのzipは展開すると `RPi_video-main/` という1階層余分なフォルダが
できるため、最初にその階層を吸収してから配置する
(ディレクトリ構造を保持するため `unzip` に `-j` は付けない)。

```
#一時フォルダへ展開
rm -rf ~/update_tmp
unzip storage/downloads/repo.zip -d ~/update_tmp

#1階層余分なフォルダ(RPi_video-main/)を吸収
mv ~/update_tmp/*/* ~/update_tmp/

#RPi用スクリプト一式を配置(setupRPi.shが参照。常に上書き)
rm -rf ~/RPiscripts
mv ~/update_tmp/RPiscripts ~/RPiscripts

#タブレット用スクリプト本体を.shortcutsへ配置(常に上書き)
mv ~/update_tmp/*.sh .shortcuts/

#VERSIONも常に上書き
mv ~/update_tmp/VERSION setting/

#認証情報・接続先一覧は、既に編集済みの場合は上書きしない
[ -f setting/sshSetting.txt ] || mv ~/update_tmp/sshSetting.txt setting/
[ -f setting/HostTable.csv ]  || mv ~/update_tmp/HostTable.csv setting/
[ -f setting/IP.txt ]         || mv ~/update_tmp/IP.txt setting/

#後片付け
rm -rf ~/update_tmp
rm storage/downloads/repo.zip

#※旧バージョンからの更新の場合、setting/MAChostTable.csvは不要になったため削除してよい
#※ ~/RPiscripts/ の内容のみ更新したい場合も、上記の取得・配置フローを使う
```

**初回セットアップの場合**、配布物の `sshSetting.txt`・`HostTable.csv` は
空のテンプレートなので、配置後に必ず内容を記入すること(後述の各セクション参照)。


## setting/フォルダに配置するファイル一覧

- IP.txt        : connect.sh実行時に自動生成される(RPi_ID, IP)。手動編集不要
- sshSetting.txt: SSH接続用の認証情報(user=, pass=)。配布時は空のため、初回に記入する
- HostTable.csv : 接続先RPiのID(英数字、例: UT01)とIPアドレスの対応表。配布時はIP列が空のため、初回に記入する
- VERSION       : タブレット側スクリプトのバージョン


## 認証情報(SSHユーザー名・パスワード)を変更する場合

SSHのユーザー名/パスワードは setting/sshSetting.txt の1か所のみで管理している。
.bashrcのssh2raspi()関数がこのファイルをsourceして読み込むため、
他のスクリプトを書き換える必要はない。

1. タブレット側: setting/sshSetting.txt を編集する
   ```
   user=(ユーザー名)
   pass=(パスワード)
   ```

2. RPi側: 対応するLinuxユーザーのパスワードを変更する
   (RPi上で) passwd コマンドを実行し、1.で設定したパスワードと一致させる

※複数のRPiで同じ認証情報を共有運用している場合、全てのRPiで
  手順2を実施しないと一部の機体に接続できなくなるので注意。OSの書き込みの際に設定すると良い


## HostTable.csvについて

host,IP の2列CSV。1行目はヘッダ。
host列には接続先RPiのID(英数字。例: UT01, UT02)、IP列にはルーター側で
固定割当したIPアドレスを記入する。

例:
```
host,IP
UT01,192.168.1.101
UT02,192.168.1.102
```

connect.sh実行時、IPが記入されている行に対してpingを行い、応答のある
機体だけが選択肢として表示される。応答がない場合や、未登録のIDに接続
したい場合は、手動でIDを入力する方式にフォールバックする。


## 各スクリプトの概要

- connect.sh     : 接続先RPiの選択(自動検出+選択 or 手動入力)→SSH接続確認
                    →SDカード容量チェック→現在時刻確認・設定→プレビュー開始
- setupRPi.sh    : 接続先RPiの選択→RPi側script/フォルダの転送(セットアップ/更新)
- recording.sh   : カメラ起動テスト→撮影対象名/メタデータ入力→音声録音の
                    有無確認→撮影開始
- cameraSetting.sh: width/height/framerate/bitrate/video_duration/
                    video_number/audio_deviceの変更
- dataCheck.sh   : 撮影データフォルダの一覧表示・サムネイルダウンロード・削除
- reboot.sh      : RPiの再起動
- shutdown.sh    : RPiのシャットダウン

## setupRPi.shについて(RPi側スクリプトのセットアップ・更新)

接続先RPiを選択した後、以下を選ぶダイアログが表示される。

- 初期セットアップ(パッケージインストール含む)
    新規RPiの場合に選択する。以下を行う。
      - ~/RPiscripts/script を RPi の ~/script に転送
      - recordフォルダの作成
      - 必要パッケージのインストール
        (python3-picamera2, rpicam-apps, alsa-utils)
- スクリプト更新のみ
    既存RPiのスクリプトだけを最新化する場合に選択する。
      - ~/RPiscripts/script を RPi の ~/script に転送

※どちらを選んでも、RPi側に既にimageSetting.txtが存在する場合は
  上書きしない(機体ごとに調整したwidth/bitrate等の設定を保持する)。
  新規セットアップ時のみ、転送したデフォルト値のimageSetting.txtが使われる。

※パッケージインストール時、RPi上のユーザーがsudoをパスワード無しで
  実行できる設定(Raspberry Pi OSのデフォルト)であることを前提にしている。

※script/フォルダ内でファイルを削除・リネームした場合、転送先のRPiには
  古いファイルが残る(scpはコピー先の不要ファイルを削除しない)。
  削除したい場合はRPi側で手動削除すること。


## Termuxショートカット化

.shortcuts フォルダ内のスクリプトに実行権限を付与すると、Termux:Widget
からホーム画面にショートカットを配置できる。

```
chmod +x .shortcuts/*.sh
```
