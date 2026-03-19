#!/bin/bash
# Checks if maintenance is overdue by reading the maintenance journal.
# Outputs a reminder if last session was > 7 days ago.
# Used as a user-prompt-submit hook in Claude Code.

JOURNAL="data/cache/maintenance_journal.json"
THRESHOLD_DAYS=7

# If journal doesn't exist, maintenance has never run
if [ ! -f "$JOURNAL" ]; then
    echo "Maintenance has never been run. Consider running /autonomous-maintenance."
    exit 0
fi

# Get the last session date
LAST_DATE=$(python3 -c "
import json, sys
try:
    j = json.load(open('$JOURNAL'))
    sessions = j.get('sessions', [])
    if not sessions:
        print('NEVER')
    else:
        print(sessions[-1].get('date', 'NEVER'))
except Exception:
    print('NEVER')
" 2>/dev/null)

if [ "$LAST_DATE" = "NEVER" ]; then
    echo "Maintenance has never been run. Consider running /autonomous-maintenance."
    exit 0
fi

# Calculate days since last maintenance
DAYS_AGO=$(python3 -c "
from datetime import datetime, date
try:
    last = datetime.strptime('$LAST_DATE', '%Y-%m-%d').date()
    delta = (date.today() - last).days
    print(delta)
except Exception:
    print(999)
" 2>/dev/null)

if [ "$DAYS_AGO" -gt "$THRESHOLD_DAYS" ]; then
    echo "Last maintenance was ${DAYS_AGO} days ago (${LAST_DATE}). Consider running /autonomous-maintenance."
fi
