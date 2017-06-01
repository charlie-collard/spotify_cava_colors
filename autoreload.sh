#!/bin/bash

interface=org.freedesktop.Notifications

trap -- '' SIGUSR1
dbus-monitor "interface='$interface'" |
while read -r line; do
    if [[ $line =~ Spotify ]]; then spotify_cava_colors; fi
done
