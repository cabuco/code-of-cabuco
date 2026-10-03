#!/usr/bin/env bash
# Dynamically resolves script directory so it runs regardless of invocation path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

health() { curl -fs http://localhost:8501/_stcore/health >/dev/null 2>&1; }

if health; then echo "EvO already running on port 8501"; exit 0; fi

pkill -f "streamlit run mapper.py" 2>/dev/null || true
sleep 1
nohup setsid python3 -m streamlit run mapper.py --server.headless true --server.port 8501 \
  > /tmp/evo-server.log 2>&1 < /dev/null &
disown

for _ in $(seq 1 30); do
  if health; then echo "EvO is up on port 8501"; exit 0; fi
  sleep 1
done
echo "EvO did NOT become healthy within 30s. Last log lines:"
tail -30 /tmp/evo-server.log
exit 1
