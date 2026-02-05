FROM python:3.9-slim
WORKDIR /app
COPY . .
# ✅ ដំឡើង grpcio និង grpcio-tools
RUN pip install --no-cache-dir grpcio grpcio-tools
# ✅ បញ្ជាឱ្យបង្កើត Proto files បើមិនទាន់មាន
RUN python -m grpc_tools.protoc -I. --python_out=./protos --grpc_python_out=./protos risk_engine.proto
CMD ["python", "main.py"]