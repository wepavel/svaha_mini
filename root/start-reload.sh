#! /usr/bin/env sh
set -e

if [ -f /app/app/main.py ]; then
    DEFAULT_MODULE_NAME=app.main
elif [ -f /app/main.py ]; then
    DEFAULT_MODULE_NAME=main
fi

PRE_START_PATH='/app/root/prestart.sh'
echo "Checking for script in $PRE_START_PATH"

MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-80}
LOG_LEVEL=${LOG_LEVEL:-info}


# If there's a prestart.sh script in the /app directory or other path specified, run it before starting
PRE_START_PATH=${PRE_START_PATH:-/app/prestart.sh}

ls_result=$(ls)
echo "LS $ls_result"

ls_result=$(pwd)
echo "PWD $ls_result"

if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . "$PRE_START_PATH"
else
    echo "There is no script $PRE_START_PATH"
fi

echo "MODULE_NAME" ${MODULE_NAME:-$DEFAULT_MODULE_NAME}
echo "APP_MODULE" $APP_MODULE

# Start Uvicorn
# exec uvicorn --host $HOST --port $PORT --log-level info --use-colors --reload --proxy-headers --forwarded-allow-ips='*' "$APP_MODULE"

exec uvicorn --host $HOST --port $PORT --log-level info --use-colors --log-config "log_config.json" --reload --proxy-headers --forwarded-allow-ips='*' "$APP_MODULE"