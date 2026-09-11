# 서버 자동 실행 배포 안내

이 문서는 Ubuntu VPS에서 월별 실행 계획을 생성하는 방법입니다. 기본 구성은 주문을 보내지 않는 `DRY_RUN`입니다.

## 구성

```text
systemd timer (매월 1일 10:30 KST)
  -> smart-etf-rebalancer.service
     -> scripts/run-scheduled.sh
        -> invest_bot run
           -> 토스증권 Open API / data/runs/*.json
```

서버의 공인 IP를 토스증권 WTS의 Open API 허용 IP에 등록해야 합니다. 허용 목록 밖의 IP 요청은 토스 API에서 차단됩니다. [토스증권 Open API 가이드](https://developers.tossinvest.com/)

## 최초 설치

Ubuntu 22.04 이상과 고정 공인 IP를 준비합니다. 아래 명령은 `root` 또는 `sudo` 권한이 있는 계정에서 실행합니다.

```bash
sudo adduser --system --group --home /opt/smart-etf-rebalancer smart-etf
sudo git clone https://github.com/sseokpyo/smart-etf-rebalancer.git /opt/smart-etf-rebalancer
sudo chown -R smart-etf:smart-etf /opt/smart-etf-rebalancer
sudo install -d -m 700 -o smart-etf -g smart-etf /opt/smart-etf-rebalancer/data
sudo -u smart-etf python3 -m venv /opt/smart-etf-rebalancer/.venv
sudo -u smart-etf /opt/smart-etf-rebalancer/.venv/bin/pip install -r /opt/smart-etf-rebalancer/requirements.txt
sudo install -d -m 700 -o root -g smart-etf /etc/smart-etf-rebalancer
sudo install -m 640 -o root -g smart-etf /opt/smart-etf-rebalancer/.env.example /etc/smart-etf-rebalancer/environment
sudo install -m 644 deploy/systemd/smart-etf-rebalancer.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/smart-etf-rebalancer.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-etf-rebalancer.timer
```

`/etc/smart-etf-rebalancer/environment`에 실제 값을 설정합니다. 이 파일은 Git에 넣지 않습니다.

```ini
TOSS_CLIENT_ID=발급받은_값
TOSS_CLIENT_SECRET=발급받은_값
TOSS_ACCOUNT_SEQ=
DRY_RUN=true
MONTHLY_BUDGET_KRW=100000
CASH_BUFFER_RATE=0.02
MIN_ORDER_USD=1.00
DRAWDOWN_LOOKBACK_DAYS=252
```

그 뒤 토스증권 WTS에서 서버의 고정 공인 IP를 허용 목록에 추가하고, 다음 명령으로 API 연결만 확인합니다.

```bash
sudo -u smart-etf -H bash -c 'cd /opt/smart-etf-rebalancer && .venv/bin/python -m invest_bot check'
```

## 검증과 운영

첫 월간 실행 전에는 다음을 실행해 타이머와 계획 파일을 확인합니다.

```bash
sudo systemctl start smart-etf-rebalancer.service
sudo journalctl -u smart-etf-rebalancer.service -n 100 --no-pager
sudo -u smart-etf ls -l /opt/smart-etf-rebalancer/data/runs/
systemctl list-timers smart-etf-rebalancer.timer
```

정기 실행 시각은 `deploy/systemd/smart-etf-rebalancer.timer`의 `OnCalendar`에서 정합니다. 현재 값은 한국 시간 매월 1일 10:30이며 주문을 전송하지 않는 점검용 시각입니다. 미국 장중 실행이나 휴장일 처리 규칙을 확정한 뒤 변경하세요.

코드 업데이트 후에는 다음 순서로 반영합니다.

```bash
sudo -u smart-etf git -C /opt/smart-etf-rebalancer pull --ff-only origin develop
sudo -u smart-etf /opt/smart-etf-rebalancer/.venv/bin/pip install -r /opt/smart-etf-rebalancer/requirements.txt
sudo systemctl restart smart-etf-rebalancer.timer
```

## 실주문 전환

실주문은 두 설정을 함께 변경해야 합니다.

1. `/etc/smart-etf-rebalancer/environment`에서 `DRY_RUN=false`로 변경합니다.
2. `/etc/systemd/system/smart-etf-rebalancer.service`의 `Environment=RUN_MODE=dry-run`을 `Environment=RUN_MODE=live`로 변경합니다.

변경 후 `sudo systemctl daemon-reload`을 실행합니다. 같은 달 중복 실행은 `data/ledger/`의 실행 저널로 차단됩니다. 주문 오류나 서버 장애 뒤에는 타이머를 재실행하지 말고 토스 주문 내역과 저널을 먼저 대조하세요.

## 중지와 복구

자동 실행을 중지하려면 다음을 실행합니다.

```bash
sudo systemctl disable --now smart-etf-rebalancer.timer
```

다음 실행만 막으려면 타이머만 중지합니다. 이미 실행 중인 서비스의 주문 상태는 토스 주문 내역과 `data/ledger/`를 확인한 뒤 판단합니다.
