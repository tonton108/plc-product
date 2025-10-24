# Raspberry Piデプロイメントガイド

**作成日:** 2025-10-24

## ラズパイへの一括デプロイ

### 1. IPアドレスリスト作成

`plc-dashboard/raspi_agent/ip_list.csv` にラズパイのIPアドレスを記載：

```csv
ip_address
192.168.0.101
192.168.0.102
192.168.0.103
```

### 2. デプロイスクリプト実行

```bash
cd plc-dashboard/raspi_agent
bash scp_bulk_push.sh
```

**スクリプトの動作:**
1. プロジェクトフォルダを `/home/pi/` に転送
2. `plc_ui.service` を `/etc/systemd/system/` に設置
3. systemd経由でDocker Composeを自動起動・永続化

### 3. systemdサービス確認

```bash
# ラズパイにSSH接続
ssh pi@192.168.0.101

# サービス状態確認
sudo systemctl status plc_ui.service

# ログ確認
sudo journalctl -u plc_ui.service -n 50
```

## 手動デプロイ

### 1. SSH鍵設定

```bash
# SSH鍵生成（初回のみ）
ssh-keygen -t rsa

# 公開鍵をラズパイにコピー
ssh-copy-id pi@192.168.0.101
```

### 2. ファイル転送

```bash
# プロジェクトフォルダを転送
scp -r plc-dashboard/raspi_agent pi@192.168.0.101:/home/pi/

# systemdサービスファイルを転送
scp plc-dashboard/raspi_agent/plc_ui.service pi@192.168.0.101:/home/pi/
```

### 3. systemdサービス設定

```bash
# ラズパイにSSH接続
ssh pi@192.168.0.101

# サービスファイルを移動
sudo mv /home/pi/plc_ui.service /etc/systemd/system/

# systemdリロード
sudo systemctl daemon-reload

# サービス有効化・起動
sudo systemctl enable plc_ui.service
sudo systemctl start plc_ui.service
```

## トラブルシューティング

### サービスが起動しない

```bash
# ログ確認
sudo journalctl -u plc_ui.service -n 100

# サービスファイルの権限確認
ls -la /etc/systemd/system/plc_ui.service

# サービスファイルの内容確認
cat /etc/systemd/system/plc_ui.service
```

### SSH接続エラー

```bash
# ネットワーク疎通確認
ping 192.168.0.101

# SSH鍵認証確認
ssh -v pi@192.168.0.101
```

詳細は `_docs/plc-knowledge/troubleshooting.md` を参照。

## 関連ドキュメント

- `_docs/deployment/environment-variables.md` - 環境変数設定
- `_docs/architecture/raspi-agent.md` - Raspberry Piエージェントアーキテクチャ
- `_docs/plc-knowledge/troubleshooting.md` - トラブルシューティング

---

**最終更新:** 2025-10-24
