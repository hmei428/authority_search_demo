#!/bin/bash

# 权威Query查询系统启动脚本

echo "======================================"
echo "权威Query查询系统"
echo "======================================"
echo ""

# 检查Python版本
echo "检查Python环境..."
python3 --version

# 检查是否已安装依赖
if [ ! -d "venv" ]; then
    echo ""
    echo "首次运行，创建虚拟环境..."
    python3 -m venv venv

    echo "激活虚拟环境..."
    source venv/bin/activate

    echo "安装依赖..."
    pip install -r requirements.txt
else
    echo "激活已有虚拟环境..."
    source venv/bin/activate
fi

echo ""
echo "======================================"
echo "启动Flask服务..."
echo "======================================"
echo ""

# 进入backend目录并启动
cd backend
python app.py
