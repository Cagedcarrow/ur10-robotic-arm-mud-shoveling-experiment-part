param(
    [string]$HostIp = $env:UR10_WINDOWS_HOST_IP,
    [string]$WslDistro = "Ubuntu-22.04",
    [string]$WslWorkspacePath = "/root/ur10_ws",
    [string]$RobotIp = "192.168.56.101",
    [string]$RobotSubnet = "192.168.56.0/24",
    [string]$VerifyDeltaDeg = "0.5",
    [string]$InitialJointController = "scaled_joint_trajectory_controller",
    [switch]$LaunchRviz = $false,
    [switch]$ConfirmExecute = $true,
    [switch]$RunVerify = $true,
    [int[]]$Ports = @(50001,50002,50003,50004)
)

$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function IpToUInt32([string]$Ip) {
    $bytes = [System.Net.IPAddress]::Parse($Ip).GetAddressBytes()
    return [uint32]($bytes[0] -shl 24 -bor ($bytes[1] -shl 16) -bor ($bytes[2] -shl 8) -bor $bytes[3])
}

function InSameNetwork([string]$A, [string]$B, [int]$Prefix) {
    $mask = if ($Prefix -eq 32) { [uint32]0xFFFFFFFF } else { [uint32]([math]::Pow(2, $Prefix) - 1) }
    if ($Prefix -eq 32) {
        $networkMask = [uint32]0xFFFFFFFF
    } else {
        $networkMask = [uint32]([uint64]0xFFFFFFFF -shl (32 - $Prefix))
    }
    $ua = IpToUInt32 $A
    $ub = IpToUInt32 $B
    return (($ua -band $networkMask) -eq ($ub -band $networkMask))
}

if (-not (Test-IsAdmin)) {
    Write-Error "请使用“管理员身份运行”的 PowerShell 执行此脚本。"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($HostIp)) {
    Write-Error "未指定 HostIp。请设置参数 -HostIp 或环境变量 UR10_WINDOWS_HOST_IP。"
    exit 1
}

if (-not ($RobotSubnet -match '^(\d+\.\d+\.\d+\.\d+)/(\d{1,2})$')) {
    Write-Error "RobotSubnet 格式错误，应为 CIDR，如 192.168.56.0/24。"
    exit 1
}
$robotSubnetIp = $Matches[1]
$robotPrefix = [int]$Matches[2]
if ($robotPrefix -lt 1 -or $robotPrefix -gt 32) {
    Write-Error "RobotSubnet 掩码前缀必须在 1~32 之间。"
    exit 1
}

$defaultIpLine = (wsl.exe -d $WslDistro -- bash -lc "hostname -I 2>/dev/null | awk '{print `$1}'" ).Trim()
if (-not $defaultIpLine) {
    Write-Error "无法获取 WSL2 IPv4。请确认 WSL2 已启动并能执行: wsl.exe -d $WslDistro -- hostname -I。"
    exit 1
}
$WslIp = $defaultIpLine.Split()[0]

$hostOnSubnet = InSameNetwork -A $HostIp -B $RobotIp -Prefix $robotPrefix
if (-not $hostOnSubnet) {
    Write-Host "警告: HostIp=$HostIp 与 RobotIp=$RobotIp 不在同一子网（${RobotSubnet}）。请复核网段。"
}

$wslOnSubnet = InSameNetwork -A $WslIp -B $RobotIp -Prefix $robotPrefix
if (-not $wslOnSubnet) {
    Write-Host "警告: 检测到 WSL IP $WslIp 与机器人网段不一致，可能是容器/路由模式差异。仍继续配置端口转发。"
}

$rulePrefix = "UR10-WSL2-Proxy"

Write-Host "[1/4] 当前参数"
Write-Host "  WSL 发行版   : $WslDistro"
Write-Host "  WSL IP        : $WslIp"
Write-Host "  Host IP       : $HostIp"
Write-Host "  Robot IP      : $RobotIp"
Write-Host "  Robot Subnet  : $RobotSubnet"
Write-Host "  工作区路径   : $WslWorkspacePath"

Write-Host "[2/4] 配置 netsh portproxy ..."
foreach ($p in $Ports) {
    Write-Host "  -> 端口 $p"
    & netsh interface portproxy delete v4tov4 listenaddress=$HostIp listenport=$p | Out-Null
    & netsh interface portproxy add v4tov4 listenaddress=$HostIp listenport=$p connectaddress=$WslIp connectport=$p | Out-Null
}

Write-Host "[3/4] 配置 Windows 入站防火墙（允许从机器人网段访问 50001~50004）..."
foreach ($p in $Ports) {
    $name = "$rulePrefix-$p"
    & netsh advfirewall firewall delete rule name="$name" | Out-Null
    & netsh advfirewall firewall add rule name="$name" `
        dir=in action=allow protocol=TCP localip=$HostIp localport=$p remoteip=$robotSubnetIp/$robotPrefix
}

Write-Host "[4/4] 检查 portproxy 配置"
& netsh interface portproxy show v4tov4 | Write-Output

if (-not $RunVerify) {
    Write-Host "完成。未启用 RunVerify，不会执行 UR10 验证流程。"
    exit 0
}

$launchRvizValue = if ($LaunchRviz) { 'true' } else { 'false' }
$confirmValue = if ($ConfirmExecute) { 'true' } else { 'false' }

Write-Host "开始执行 run_full_verify.sh："
Write-Host "  ROBOT_IP=$RobotIp"
Write-Host "  REVERSE_IP=$HostIp"
Write-Host "  WRIST3_DELTA_DEG=$VerifyDeltaDeg"

$wslCommand = @"
set -euo pipefail
source /opt/ros/humble/setup.bash
if [ -f '$WslWorkspacePath/install/setup.bash' ]; then
  source '$WslWorkspacePath/install/setup.bash'
fi
cd '$WslWorkspacePath/src/ur10_real_comm/scripts'
ROBOT_IP='$RobotIp' \
REVERSE_IP='$HostIp' \
WRIST3_DELTA_DEG='$VerifyDeltaDeg' \
CONFIRM_EXECUTE='$confirmValue' \
LAUNCH_RVIZ='$launchRvizValue' \
INITIAL_JOINT_CONTROLLER='$InitialJointController' \
./run_full_verify.sh
"@.Trim()

& wsl.exe -d $WslDistro -- bash -lc $wslCommand
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "[PASS] UR10 通讯包一键验证成功。"
} else {
    Write-Host "[FAIL] UR10 通讯包一键验证失败，返回码: $exitCode"
}
exit $exitCode
