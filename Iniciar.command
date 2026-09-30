#!/bin/sh
cd "$(dirname "$0")"
./heyface up
printf '\nPressione Enter para fechar.\n'
read answer
