# YOLO Web 服务启动脚本
Write-Host "=== 启动 YOLO Web 服务 ===" -ForegroundColor Green

# 启动 Python 模型服务 (5000)
Write-Host "[1/3] 启动 Python 模型服务 (5000)..." -ForegroundColor Yellow
$pythonJob = Start-Job -ScriptBlock {
    Set-Location C:\Users\huang\Desktop\yolo-web\yolo26-api
    python app.py
}

# 等待 Python 服务启动
Start-Sleep 5

# 启动后端服务 (3000)
Write-Host "[2/3] 启动后端服务 (3000)..." -ForegroundColor Yellow
$bunJob = Start-Job -ScriptBlock {
    Set-Location C:\Users\huang\Desktop\yolo-web\server
    bun run src/index.ts
}

# 等待后端服务启动
Start-Sleep 3

# 启动前端服务 (4321)
Write-Host "[3/3] 启动前端服务 (4321)..." -ForegroundColor Yellow
$pnpmJob = Start-Job -ScriptBlock {
    Set-Location C:\Users\huang\Desktop\yolo-web
    pnpm dev
}

Write-Host ""
Write-Host "=== 所有服务已启动 ===" -ForegroundColor Green
Write-Host ""
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  前端界面: http://localhost:4321" -ForegroundColor White
Write-Host "  后端API:  http://localhost:3000" -ForegroundColor White
Write-Host "  模型服务: http://localhost:5000" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 停止所有服务" -ForegroundColor Red

# 保持脚本运行
while ($true) {
    Start-Sleep 1
}
