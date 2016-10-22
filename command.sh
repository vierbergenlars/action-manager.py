#!/bin/bash
$(echo "$1" > "$2")&
quit_proc="$!"
sleep 1
kill -9 "$quit_proc" 
