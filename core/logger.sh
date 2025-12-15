#!/bin/bash
logger.log(){
	local MODULE="$1"
	local MESSAGE="$1"

	mkdir -p logs

	# Простая реализация логирования в файлах logs/lkim.log
	echo "[$(date +'%Y-%m-%d %H:%M')] $MODULE: $MESSAGE" >> logs/lkim.log
}
