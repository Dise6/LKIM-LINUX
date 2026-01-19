#!/bin/bash
PIPE_PATH="/tmp/lkim_telemetry.fifo"
#Создание канала при запуске 
init_telemetry_pipe() {
    if [[ ! -p "$PIPE_PATH" ]]; then
        mkfifo "$PIPE_PATH"
    fi
}

# Функция отправки данных в UI
# фОРМАТ TIMESTAMP | TX_KB | RX_KB |INTEGRITY_SCORE | ALERT_ID
send_telemetry() {
    local tx=$1
    local rx=$2
    local score=$3
    local alert_id=$4

# Мы пишем в фоне, чтобы скрипт не блокировался, если  Python не успел прочитать 
    if [[ -p "$PIPE_PATH" ]]; then 
        echo -e "$(date +%s)\t$tx\t$rx\t$score\t$alert_id" > "$PIPE_PATH" &
    fi 
}

get_file_sha256() {
	local FILE_PATH="$1"
	sha256sum "$FILE_PATH" | awk '{print $1}'
}
