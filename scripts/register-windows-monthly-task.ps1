param(
    [ValidateRange(1, 28)]
    [int]$Day = 1,
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$Time = '10:30',
    [string]$TaskName = 'Smart ETF Rebalancer - Monthly Investment'
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot 'run-monthly-dry-run.cmd'

if (-not (Test-Path $launcher)) {
    throw "실행 파일을 찾을 수 없습니다: $launcher"
}
if (-not (Test-Path (Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'))) {
    throw '가상환경을 찾을 수 없습니다. 프로젝트 루트에서 python -m venv .venv 와 pip install -r requirements.txt 를 먼저 실행하세요.'
}

# schtasks starts commands from a system directory. The .cmd launcher changes
# into the project root before importing the Python package.
$command = "cmd.exe /d /c `"`"$launcher`"`""
& schtasks.exe /Create /TN $TaskName /TR $command /SC MONTHLY /D $Day /ST $Time /RL LIMITED /F
if ($LASTEXITCODE -ne 0) {
    throw "작업 스케줄러 등록에 실패했습니다. 종료 코드: $LASTEXITCODE"
}

Write-Host "등록 완료: $TaskName"
Write-Host "실행 시각: 매월 $Day 일 $Time"
Write-Host '대시보드의 자동거래가 OFF이면 계획만 만들고, ON이면 계획된 매수 주문을 전송합니다.'
