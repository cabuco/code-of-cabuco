#!/usr/bin/env bash
# Starts the Rosetta UI on port 8080
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

mkdir -p input output

health() { curl -fs http://localhost:8080/_stcore/health >/dev/null 2>&1; }

if health; then echo "Rosetta already running on port 8080"; exit 0; fi

pkill -f "streamlit run app.py" 2>/dev/null || true
sleep 1
nohup setsid python3 -m streamlit run app.py > /tmp/rosetta-server.log 2>&1 < /dev/null &
disown

for _ in $(seq 1 30); do
  if health; then echo "Rosetta is up on port 8080"; exit 0; fi
  sleep 1
done
echo "Rosetta did NOT become healthy within 30s. Last log lines:"
tail -30 /tmp/rosetta-server.log
exit 1
