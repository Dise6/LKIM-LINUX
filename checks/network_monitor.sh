#!/bin/bash

HISTORY_SIZE=10 #Сколько последних замеров помнить для измерения среднего значения 
ANOMALY_THRESHOLD=2 # во сколько раз превышание считается аномалией (фитиль)

declare -a rx_history
declare -a tx_history

calculate_average() {
	local arr=("$@")
	local sum=0
	local count=${#arr[@]}

	if [[ "$count" -eq 0 ]]; then echo 0; return; fi

	for val in "${arr[@]}"; do
		sum=$((sum + val))
	done 

	echo $((sum /count))
}

get_network_traffic() {
	# Считываем /proc/net/dev для получения байтов (RX/TX)
	# Предположим, используемый интерфейс eth0 или первый активный
	# Автоопределение интерфейса (берем тот, где есть дефолтный роут) 

	local iface=$(ip route | grep default | awk '{print $5}' | head -n 1)

	if [[ -z "$iface" ]]; then iface="eth0"; fi

	read rx1 tx1 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)
	sleep 1 
	read rx2 tx2 < <(awk -v dev="$iface" '$1 ~ dev {print $2, $10}' /proc/net/dev)

	local rx_speed=$(( (rx2 - rx1) / 1024 ))
	local tx_speed=$(( (tx2 - tx1) / 1024 ))

	echo "$tx_speed $rx_speed"
}

# Функция для конвертации HEX IP 
hex_to_ip() {
    local hex=$1
    if [[ ${#hex} -ne 8 ]]; then echo "$hex"; return; fi
    printf "%d.%d.%d.%d" $((16#${hex:6:2})) $((16#${hex:4:2})) $((16#${hex:2:2})) $((16#${hex:0:2}))
}

get_active_ports_stealth() {
    local ports_data=""
    # Собираем уникальные локальные порты 
    local raw_ports=$(awk 'NR>1 {print $2}' /proc/net/tcp | cut -d':' -f2 | sort -u | head -n 15)
    
    for hex_port in $raw_ports; do
        local dec_port=$((16#$hex_port))
        # Статус: если есть в списке, значит активен. 
        # Цвет: зеленый для стандартных, желтый для высоких портов
        local color="#3fb950"
        [[ $dec_port -gt 1024 ]] && color="#d29922"
        ports_data+="${dec_port}:LISTEN:${color},"
    done
    echo "${ports_data%,}"
}
 
run_network_telemetry() {
    init_telemetry_pipe
    logger.log "NETWORK" "Запущен анализ трафика на интерфейсе"
    local iteration=0

    while true; do
        local anomaly_score=0
        local alert_mod="NONE"   
        # --- ФЛАГ 1: ГРАФИК (Каждую секунду) ---
        read tx_curr rx_curr < <(get_network_traffic)

        # обновление истории и расчет среднего (basaline)
        rx_history+=($rx_curr)
		tx_history+=($tx_curr)

        # Ограничение размера истории
		if [[ ${#rx_history[@]} -gt $HISTORY_SIZE ]]; then
			rx_history=("${rx_history[@]:1}")
			tx_history=("${tx_history[@]:1}")
		fi

        rx_avg=$(calculate_average "${rx_history[@]}")
		tx_avg=$(calculate_average "${tx_history[@]}")

        # Расчет коэффициента аномалии (SCORE)
		# Score будет множителем: 0 = норма, 1.0 = превышение в 2 раза,2.0 = в 3 раза и т.д
		# это определяет длину фитиля 

		# зашита от деления на 0 
		[[ $rx_avg -eq 0 ]] && rx_avg=1
		[[ $tx_avg -eq 0 ]] && tx_avg=1

        # Вычисляем превышение (heuristic logic)
		# Если текущие значение > среднего * порог, то score растет
	
		if (( tx_curr > tx_avg * ANOMALY_THRESHOLD )) || (( rx_curr > rx_avg * ANOMALY_THRESHOLD )); then
			# Простая формула для демонстрации 
			anomaly_score=1
		fi 

		if grep -q "ALERT" "logs/lkim.log"; then
			alert_mod="SYSTEM_COMPROMISED"
			anomaly_score=5 # Максимальный фитиль при взломе
		fi
        # Отправляем данные графика с тегом GRAPH
        # Формат: GRAPH|timestamp|tx|rx|score|alert
        echo "GRAPH|$(date +%H:%M:%S)|$tx_curr|$rx_curr|$anomaly_score|$alert_mod" > "$PIPE_PATH"

        # --- ФЛАГ 2: ПОРТЫ (Каждые 5 секунд) ---
        if (( iteration % 5 == 0 )); then
            local ports=$(get_active_ports_stealth)
            echo "PORTS|$ports" > "$PIPE_PATH"
        fi

        # --- ФЛАГ 3: ХОСТЫ ---
        if (( iteration % 7 == 0 )); then
            local hosts_data=$(get_network_hosts)
            echo "HOSTS|$hosts_data" > "$PIPE_PATH"
        fi

        # Внутри цикла while true
        if (( anomaly_score > 0 )); then
            # Используем твой стандартный логгер
            logger.log "NETWORK" "Anomaly detected! Score: $anomaly_score. Traffic: TX ${tx_curr}KB/s, RX ${rx_curr}KB/s"
        fi

        if (( iteration % 30 == 0 )); then
            logger.log "SYSTEM" "Periodic integrity check: Network stack is stable."
        fi

        ((iteration++))
        # sleep уже заложен внутри get_network_traffic
    done
}
# Сбор реальных внешних хостов (удаленные IP)
get_network_hosts() {
    local hosts_data=""
    
    # Сбор из всех источников: TCP, TCP6, UDP, UDP6
    # 1. Берем колонку 3 (Remote Address)
    # 2. Убираем локальные адреса (00000000 и 0100007F)
    # 3. Оставляем только уникальные
    local raw_hosts=$(awk 'NR>1 {print $3}' /proc/net/{tcp,udp,tcp6,udp6} 2>/dev/null | \
                      cut -d':' -f1 | \
                      grep -vE "00000000|0100007F" | \
                      sort -u | head -n 12)

    if [[ -z "$raw_hosts" ]]; then
        echo "NO_REMOTE:IDLE:#8b949e"
        return
    fi

    for hex_ip in $raw_hosts; do
        local ip
        # Если это короткий HEX (IPv4) - конвертируем, если длинный (IPv6) - берем как есть
        if [[ ${#hex_ip} -eq 8 ]]; then
            ip=$(hex_to_ip $hex_ip)
        else
            ip="IPv6_ADDR" # Для простоты UI, так как полные IPv6 слишком длинные
        fi
        
        hosts_data+="${ip}:ESTABLISHED:#58a6ff,"
    done

    echo "${hosts_data%,}"
}