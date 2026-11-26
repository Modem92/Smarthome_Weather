#!/bin/sh
set -eu
exec sh "$(dirname -- "$0")/raspberry_pi/start_pi_widget_demo.sh" "$@"
