#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PATH="$BASE_DIR/arrolite/.env"

# 1. Load Environment Variables
if [ -f "$ENV_PATH" ]; then
    set -a
    source "$ENV_PATH"
    set +a
else
    echo "Error: .env file not found."
    exit 1
fi

# 2. Setup Vars & Defaults
DB_PORT=${DB_PORT:-3306}
BACKUP_DIR="$BASE_DIR/backups_folder"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ZIP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.zip"
TEMP_SQL="$BACKUP_DIR/temp_dump.sql"

# 3. Run Dump
export MYSQL_PWD="$DATABASE_PASSWORD"
mysqldump -u "$DATABASE_USER" -h "$DB_HOST" -P "$DB_PORT" "$DATABASE_NAME" > "$TEMP_SQL"
unset MYSQL_PWD
echo "Database Name: $DATABASE_NAME"
echo "Database User: $DATABASE_USER"
echo "Database Host: $DB_HOST"
echo "Database Port: $DB_PORT"

# 4. Zip and Clean up
if [ -s "$TEMP_SQL" ]; then # -s checks if file exists AND is not empty
    zip -j "$ZIP_FILE" "$TEMP_SQL"
    rm "$TEMP_SQL"
    echo "Success! Backup created at: $ZIP_FILE"
else
    echo "Database export failed or file is empty."
    [ -f "$TEMP_SQL" ] && rm "$TEMP_SQL"
    exit 1
fi