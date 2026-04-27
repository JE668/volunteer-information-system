#!/bin/bash
# 清除缓存并重启 Flask

echo "=== 清除缓存并重启 Flask ==="

# 1. 停止现有 Flask 进程
echo "停止现有 Flask 进程..."
pkill -f "python.*app.py" 2>/dev/null
sleep 1

# 2. 清除 Python 缓存
echo "清除 Python 缓存..."
find /Users/je/Downloads/volunteer-information-system -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /Users/je/Downloads/volunteer-information-system -type f -name "*.pyc" -delete 2>/dev/null || true

# 3. 清除 Flask 会话（如果有）
rm -rf /Users/je/Downloads/volunteer-information-system/.flaskenv 2>/dev/null || true

# 4. 启动 Flask
echo "启动 Flask..."
cd /Users/je/Downloads/volunteer-information-system
export FLASK_ENV=development
export FLASK_DEBUG=1
python3 app.py &

# 5. 等待启动
echo "等待 Flask 启动..."
sleep 3

# 6. 测试
echo ""
echo "=== 测试 Flask ==="
if curl -s "http://127.0.0.1:5000/simulate" | grep -q "gradeGrid"; then
    echo "✓ Flask 正常运行"
    echo ""
    echo "=== 请在浏览器中执行以下操作 ==="
    echo "1. 完全关闭浏览器（所有窗口）"
    echo "2. 重新打开浏览器"
    echo "3. 访问：http://127.0.0.1:5000/simulate?t=$(date +%s)"
    echo "4. 按 F12 打开开发者工具，查看 Console"
    echo "5. 应该能看到调试信息：'DOMContentLoaded triggered'"
    echo ""
    echo "或者，在 Console 中手动执行："
    echo "  renderGradeInputs();"
else
    echo "✗ Flask 启动失败，请检查日志"
fi
