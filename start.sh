#!/bin/bash
ARGS="$@"
while [[ -n "$@" ]]; do
    if [[ "${1:0:1}" != "-" ]]; then
        if [[ -z "$volumepipe" ]]; then
            volumepipe="$1"
        elif [[ -z "$commandpipe" ]]; then
            commandpipe="$1"
        fi
    fi
    shift;
done



# volumepipe
if ! [[ -p "$volumepipe" ]]; then
    rm -rf "$volumepipe"
    mkfifo "$volumepipe"
fi

# volumecontrol
if ! [[ -p "$commandpipe" ]]; then
    rm -rf "$commandpipe"
    mkfifo "$commandpipe"
fi

eval set -- "$ARGS"
exec "$(dirname "${BASH_SOURCE[0]}")/daemon.py" "$@"
