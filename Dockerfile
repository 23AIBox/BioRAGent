# 使用官方 Python 3.10 精简镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制全部项目文件
COPY . .

# 设置启动命令（如果你用的是 main_test.py 作为入口）
CMD ["python", "agent_core/agent_main.py"]