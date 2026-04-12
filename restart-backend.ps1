# 重启后端和Python服务 - 两个独立终端窗口
Write-Host "=== 重启后端和Python服务 ===" -ForegroundColor Green

# 函数：停止占用特定端口的进程
function Stop-ProcessOnPort($port, $name) {
    Write-Host "停止 $name (端口 $port)..." -ForegroundColor Yellow
    try {
        $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($connection) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $process.Id -Force
                Write-Host "  ✓ 已停止进程: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Green
            }
        } else {
            Write-Host "  - 端口 $port 未被占用" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  - 端口 $port 无需清理" -ForegroundColor Gray
    }
}

# 停止现有服务
Write-Host "`n[1/2] 停止现有服务..." -ForegroundColor Cyan
Stop-ProcessOnPort 5000 "Python模型服务"
Stop-ProcessOnPort 3000 "后端服务"

# 额外清理可能残留的进程
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "bun" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep 2

# 启动两个独立的终端窗口
Write-Host "`n[2/2] 启动新服务..." -ForegroundColor Cyan

# Python 模型服务 (端口 5000) - 蓝色窗口
Write-Host "  → 启动 Python 模型服务 (端口 5000)" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== Python模型服务 (端口5000) ===' -ForegroundColor Blue; Set-Location 'C:\Users\huang\Desktop\yolo-web\yolo26-api'; python app.py"

Start-Sleep 3

# 后端服务 (端口 3000) - 绿色窗口
Write-Host "  → 启动后端服务 (端口 3000)" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host '=== 后端服务 (端口3000) ===' -ForegroundColor Green; Set-Location 'C:\Users\huang\Desktop\yolo-web\server'; bun start"

Write-Host "`n=== 两个服务已启动 ===" -ForegroundColor Green
Write-Host "`n访问地址:" -ForegroundColor Cyan
Write-Host "  后端API:  http://localhost:3000" -ForegroundColor White
Write-Host "  模型服务: http://localhost:5000" -ForegroundColor White
Write-Host "`n两个独立的 PowerShell 窗口已打开" -ForegroundColor Yellow
