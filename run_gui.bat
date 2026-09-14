@echo off
chcp 65001 >nul
echo 正在启动 A股策略回测工具 ...
python gui.py
if errorlevel 1 (
    echo.
    echo 启动失败。请先安装依赖:  pip install -r requirements.txt
    pause
)
