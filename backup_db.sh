#!/bin/bash

# Get the folder where this script lives (project_folter/)
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define the relative path to the .env file
ENV_PATH="$BASE_DIR/arrolite/.env"

# 1. Load the .env file
if [ -f "$ENV_PATH" ]; then
    export $(grep -v '^#' "$ENV_PATH" | xargs)
    echo "Loaded configuration from $ENV_PATH"
else
    echo "Error: .env file not found at $ENV_PATH"
    exit 1
fi

# 2. Setup Backup Directory inside project_folter/
BACKUP_DIR="$BASE_DIR/backups_folder"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ZIP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.zip"
TEMP_SQL="$BACKUP_DIR/temp_dump.sql"

# 3. Run MySQL Dump using .env variables
echo "Backing up database: $DATABASE_NAME..."
mysqldump -u "$DATABASE_USER" -p"$DATABASE_PASSWORD" -h "$DB_HOST" --port "$DB_PORT" "$DATABASE_NAME" > "$TEMP_SQL"

# 4. Zip and Clean up
if [ -f "$TEMP_SQL" ]; then
    zip -j "$ZIP_FILE" "$TEMP_SQL"
    rm "$TEMP_SQL"
    echo "Success! Backup created at: $ZIP_FILE"
else
    echo "Database export failed. Check your .env credentials."
    exit 1
fi