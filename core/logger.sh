#!/bin/bash

LOG_DIR="logs"
LOG_FILE="$LOG_DIR/lkim.log"

logger.log(){
	local MODULE="$1"
	local MESSAGE="$2"

	mkdir -p "$LOG_DIR"

	local LOG_ENTRY="[$(date +'%Y-%m-%d %H:%M:%S')] [$MODULE] $MESSAGE"
	# Простая реализация логирования в файлах logs/lkim.log
	echo "$LOG_ENTRY" >> "$LOG_FILE"

      local COLOR_RESET='\033[0m'
      local COLOR_RED='\033[31m'
      local COLOR_YELLOW='\033[33m'

      case "MODULE" in
	"ERROR")
		echo -e "${COLOR_RED}$LOG_ENTRY${COLOR_RESET}" >&2
		;;
	"ALERT")
		echo -e "${COLOR_YELLOW}$LOG_ENTRY${COLOR_RESET}"
		;;
	*)
		echo "$LOG_ENTRY"
		;;
        esac
}
