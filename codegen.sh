#!/bin/sh
# codegen.sh: Generate the stormgate_pb2 python module for reading stormgate protobuf.

# Haven't bothered integrating this with the python package build, should
# change rarely enough that a manual rebuild is fine.

protoc --python_out=shroudstone --pyi_out=shroudstone stormgate.proto
