#!/bin/bash
# Use this to generate the *.py and *.pyi files needed for the generator to run.
pip3 install grpcio-tools
python3 -m grpc_tools.protoc telemetry.proto -I=. --python_out=. --grpc_python_out=. --pyi_out=.
python3 -m grpc_tools.protoc mdt_grpc_dialout.proto -I=. --python_out=. --grpc_python_out=. --pyi_out=.
