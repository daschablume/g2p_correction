#!/bin/bash
# entrypoint.sh

# Exit on any error
set -e

# Function to check if the database is already initialized
check_db_initialized() {
    # Check if the migrations directory exists
    if [ -d "app/migrations" ]; then
        echo "Database already initialized."
        return 0
    else
        return 1
    fi
}

# Initialize the database only if it has not been initialized
if ! check_db_initialized; then
    echo "Initializing the database..."
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
else
    echo "Skipping database initialization."
fi

# Start a bash shell
exec "$@"