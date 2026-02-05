import sys
import os
import logging
import grpc
from concurrent import futures

# បន្ថែម Path ឱ្យ Python រកឃើញកូដ gRPC
sys.path.append(os.path.join(os.path.dirname(__file__), "protos"))

import risk_engine_pb2
import risk_engine_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

class RiskEngineService(risk_engine_pb2_grpc.RiskEngineServicer):
    # ✅ ត្រូវតែ Indent ចូលក្នុង Class បែបនេះ
    def CheckRisk(self, request, context):
        logger.info(f"🤖 AI Request: User={request.username}, Amount=${request.amount}")
        
        if request.amount >= 10000:
            logger.warning("   🚫 High Risk -> BLOCK")
            return risk_engine_pb2.RiskResponse(risk_level="HIGH", action="BLOCK")
        
        logger.info("   ✅ Low Risk -> ALLOW")
        return risk_engine_pb2.RiskResponse(risk_level="LOW", action="ALLOW")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    risk_engine_pb2_grpc.add_RiskEngineServicer_to_server(RiskEngineService(), server)
    server.add_insecure_port('[::]:50051')
    logger.info("🚀 Python Risk Engine running on port 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()