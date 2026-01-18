import sys
import os
import logging
import grpc
from concurrent import futures

# 🛠️ SETUP PATH: Ensure Python can find the generated code in 'protos/'
sys.path.append(os.path.join(os.path.dirname(__file__), "protos"))

# Import generated classes
import risk_engine_pb2
import risk_engine_pb2_grpc

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

class RiskEngineService(risk_engine_pb2_grpc.RiskEngineServicer):
    """
    Implementation of the RiskEngine service defined in the .proto file.
    """

def CheckRisk(self, request, context):
        print(f"🤖 AI Request: User={request.username}, Amount=${request.amount}")

        # ❌ កូដចាស់ (អាចខុសត្រង់នេះ):
        # if request.amount > 20000: (២ ម៉ឺនគត់ វានឹងឱ្យរួចខ្លួន)

        # ✅ កូដថ្មី (កែដាក់ >= 10000):
        # មានន័យថា៖ ចាប់ពី ១ ម៉ឺនឡើងទៅ គឺ BLOCK ទាំងអស់!
        if request.amount >= 10000:
            print("   🚫 High Risk (Amount too high) -> BLOCK")
            return risk_engine_pb2.RiskResponse(risk_level="HIGH", action="BLOCK")
        
        # បើក្រោម ១ ម៉ឺន គឺ ALLOW
        print("   ✅ Low Risk -> ALLOW")
        return risk_engine_pb2.RiskResponse(risk_level="LOW", action="ALLOW")
def serve():
    """
    Starts the gRPC Server.
    """
    # Create a gRPC server with a thread pool (10 workers handles concurrent requests)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Register our service class
    risk_engine_pb2_grpc.add_RiskEngineServicer_to_server(RiskEngineService(), server)
    
    # Listen on port 50051
    server.add_insecure_port('[::]:50051')
    logger.info("🚀 Python Risk Engine (gRPC) running on port 50051...")
    
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()