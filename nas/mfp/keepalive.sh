#!/bin/sh
# Faesst die MFP-Session alle 10 Minuten an (Grenze: ~30 min ohne Aufruf) und verlaengert bei Bedarf.
# Laeuft als eigener Container mit demselben Image und demselben /config-Volume wie der Server.
INTERVAL="${KEEPALIVE_INTERVAL:-600}"
while true; do
  python /app/mfp_session.py status || echo "$(date -u +%FT%TZ) keepalive: Session nicht verlaengerbar, neuer Login noetig"
  sleep "$INTERVAL"
done
