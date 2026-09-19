#!/bin/bash
# Copyright (c) 2018 Felix Almeida (white-glider)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

umask 077
WORK_DIR=
CHILD_PID=

cleanup() {
    if [[ -n "$CHILD_PID" ]]; then
        kill "$CHILD_PID" 2>/dev/null || :
        wait "$CHILD_PID" 2>/dev/null || :
    fi
    if [[ -n "$WORK_DIR" ]]; then
        rm -rf -- "$WORK_DIR"
    fi
}
trap 'cleanup' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

notify() {
    notify-send --urgency=critical --category=email --icon=dialog-warning -- "$1" "$2" ||
        printf '%s\n' 'clamav_evolution: desktop notification failed.' >&2
}
fail() {
    printf 'clamav_evolution: %s\n' "$1" >&2
    notify 'ClamAV: e-mail scan failed' "$1"
    exit 2
}

for dependency in clamscan awk readlink mktemp cat; do
    command -v "$dependency" >/dev/null 2>&1 || fail "Missing command: $dependency"
done
SCRIPT=$(readlink -f -- "$0") || fail 'Cannot resolve the script path.'
AWK_FILE="${SCRIPT%.*}.awk"
[[ -r "$AWK_FILE" ]] || fail "Missing AWK counterpart: $AWK_FILE"
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/clamav-evolution.XXXXXXXXXX") ||
    fail 'Cannot create private temporary storage.'
MSG="$WORK_DIR/message"
RSLT="$WORK_DIR/result"

# Explicit stdin redirection preserves the message for the background child.
exec 3<&0
cat <&3 3<&- > "$MSG" &
CHILD_PID=$!
exec 3<&-
wait "$CHILD_PID"
STATUS=$?
CHILD_PID=
[[ "$STATUS" -eq 0 ]] || fail 'Cannot save the message for scanning.'

clamscan --no-summary --detect-pua=yes --official-db-only=yes -- "$MSG" > "$RSLT" 2>&1 &
CHILD_PID=$!
wait "$CHILD_PID"
STATUS=$?
CHILD_PID=
case "$STATUS" in
    0) exit 0 ;;
    1)
        THREAT=$(awk '/ FOUND$/ { sub(/^.*: /, ""); sub(/ FOUND$/, ""); print }' "$RSLT")
        STRING=$(awk -f "$AWK_FILE" "$MSG")
        # Escape notification markup in untrusted message fields.
        TEXT="$THREAT"$'\n'"$STRING"
        TEXT=${TEXT//&/\&amp;}
        TEXT=${TEXT//</\&lt;}
        TEXT=${TEXT//>/\&gt;}
        notify 'ClamAV: e-mail threat detected!' "$TEXT"
        exit 1
        ;;
    *)
        cat -- "$RSLT" >&2
        fail "ClamAV did not complete successfully (exit $STATUS). The message was not verified clean."
        ;;
esac
