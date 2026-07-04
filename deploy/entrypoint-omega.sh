#!/bin/sh
# OmegaEngine Docker entrypoint
set -e

if [ $# -eq 0 ]; then
    echo "BlackHornet Omega — Docker Image"
    echo "Usage: docker run bh-omega <command>"
    echo ""
    echo "Commands:"
    echo "  start        Boot and run the autonomous loop"
    echo "  status       Show engine status"
    echo "  score        Show project scores"
    echo "  sync         Run ecosystem sync"
    echo "  loop         Run single main loop iteration"
    echo "  bh-omega ... Pass through to bh-omega CLI"
    echo ""
    echo "Example:"
    echo "  docker run bh-omega start --loop 5"
    exit 0
fi

exec "$@"
