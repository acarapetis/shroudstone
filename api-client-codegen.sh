#!/bin/bash
# This script updates the stormgateworld API client to match the latest schema,
# without clobbering anything else.
# You need to set up an alias/script openapi-generator-cli which does the equivalent of
# java -jar openapi-generator-cli.jar "$@".
openapi-generator-cli generate -g python -i https://api.stormgateworld.com/api-docs/openapi.json --package-name shroudstone.stormgateworld --output _openapi_tmp
cp -rT _openapi_tmp/shroudstone/stormgateworld shroudstone/stormgateworld
rm -r _openapi_tmp
