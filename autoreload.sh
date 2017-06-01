#!/bin/bash

interface=org.freedesktop.Notifications

trap -- '' SIGUSR1
dbus-monitor --profile "interface='$interface'" |
while read -r line; do
    spotify_cava_colors
done
