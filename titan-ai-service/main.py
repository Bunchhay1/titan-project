import grpc
from concurrent import futures
import sys
import os

# 🚀 ដំណោះស្រាយសម្រាប់ ModuleNotFoundError:
# បន្ថែម Folder 'protos' ទៅក្នុង Search Path របស់ Python
sys.path.append(os.path.join(os.path.dirname(__file__), 'protos'))

try:
    import risk_engine_pb2 as pb2
    import risk_engine_pb2_grpc as pb2_grpc
except ImportError:
    # Fallback សម្រាប់ករណី Import តាមរយៈ Package
    import protos.risk_engine_pb2 as pb2
    import protos.risk_engine_pb2_grpc as pb2_grpc

class RiskService(pb2_grpc.RiskEngineServiceServicer):
    def CheckRisk(self, request, context):
        # 🧠 ឡូហ្សិក AI របស់មេបញ្ជាការ៖ បច្ចុប្បន្នគឺ Default ALLOW
        print(f"📡 Analyzing risk for User: {request.user_id}, Amount: {request.amount}")
        
        # ឆ្លើយតបទៅកាន់ Java (ត្រូវតែ match ជាមួយ risk_engine.proto)
        return pb2.RiskCheckResponse(
            risk_score=10,
            risk_level="LOW",
            action="ALLOW"
        )

def serve():
    # បង្កើត gRPC Server ជាមួយ 10 Threads
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_RiskEngineServiceServicer_to_server(RiskService(), server)
    
    # បើក Port 50051 (ត្រូវនឹង titan.ai.port ក្នុង Java)
    server.add_insecure_port('[::]:50051')
    print("🤖 Titan AI Service is running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()