# Windows PC 월간 자동 실행

이 방식은 Windows 작업 스케줄러가 PC에서 봇을 실행합니다. PC가 켜져 있거나 절전 해제가 가능한 상태여야 합니다. PC 전원이 완전히 꺼져 있으면 실행되지 않습니다.

## 사전 준비

프로젝트 루트에서 한 번만 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 토스 Open API 값을 입력하되, 처음에는 반드시 `DRY_RUN=true`를 유지합니다. 토스증권 WTS의 Open API 허용 IP에는 이 PC가 인터넷에 연결될 때 사용하는 공인 IP를 등록합니다.

## 월간 DRY_RUN 등록

프로젝트 루트에서 다음 명령을 실행합니다.

```powershell
.\scripts\register-windows-monthly-task.ps1
```

기본 실행 시각은 매월 1일 10:30입니다. 다른 날짜와 시각을 지정하려면 다음처럼 실행합니다.

```powershell
.\scripts\register-windows-monthly-task.ps1 -Day 5 -Time '21:30'
```

등록된 작업은 `Smart ETF Rebalancer - Monthly Dry Run`이며 `scripts/run-monthly-dry-run.cmd`를 실행합니다. 이 실행 파일은 `--live`를 전달하지 않으므로 주문을 보내지 않습니다.

## 첫 실행 확인

Windows 검색에서 **작업 스케줄러**를 열고 `작업 스케줄러 라이브러리`에서 등록된 작업을 찾습니다. 해당 작업을 마우스 오른쪽 버튼으로 눌러 **실행**한 뒤, 프로젝트의 `data/runs/`에 새 JSON 계획 파일이 생기는지 확인합니다.

## PC 전원 설정

작업 스케줄러에서 작업을 열고 **조건** 탭에서 `작업을 실행하기 위해 컴퓨터 깨우기`를 선택할 수 있습니다. 이 설정은 절전 상태에서만 동작합니다. 완전히 종료된 PC는 자동 실행할 수 없습니다.

## 중지 또는 제거

다음 명령으로 자동 실행을 제거합니다.

```powershell
schtasks /Delete /TN "Smart ETF Rebalancer - Monthly Dry Run" /F
```

## 실주문

PC 자동 실행은 충분한 DRY_RUN 검증 전까지 주문 용도로 사용하지 않습니다. 실주문 전환은 토스 앱의 주문 내역과 월간 실행 계획을 여러 번 대조한 뒤 별도 절차로 진행합니다.
