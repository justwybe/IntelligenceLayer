#!/bin/bash
# Sets ANTHROPIC_API_KEY in .env by reading from stdin.
# Useful on RunPod where the web terminal is too narrow to paste long commands.
ENV_FILE="${1:-/root/IntelligenceLayer/.env}"

echo -n "Paste your ANTHROPIC_API_KEY: "
read -r KEY

sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${KEY}|" "$ENV_FILE"

echo "Updated. Verify:"
grep ANTHROPIC_API_KEY "$ENV_FILE"
