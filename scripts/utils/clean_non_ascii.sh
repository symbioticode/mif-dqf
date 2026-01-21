#!/usr/bin/env bash
# Nettoie caractères non-ASCII d'un fichier Python

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "Usage: $0 <file.py>"
    exit 1
fi

# Backup
cp "$FILE" "$FILE.bak"

# Nettoyer (remplace non-ASCII par espace)
iconv -f UTF-8 -t ASCII//TRANSLIT "$FILE.bak" > "$FILE"

echo "✅ Nettoyé: $FILE"
echo "📦 Backup: $FILE.bak"
