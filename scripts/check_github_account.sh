#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Vérification compte GitHub..."
git remote -v
ssh -T github.com-symbioticode 2>&1 | grep "Hi symbioticode" && echo "✅ SSH OK" || echo "❌ SSH KO"
