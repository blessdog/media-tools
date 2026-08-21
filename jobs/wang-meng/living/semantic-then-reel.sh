#!/usr/bin/env zsh
set -e
cd "$(dirname "$0")/../../.."
jobs/wang-meng/living/build-semantic-masks.sh z3w
jobs/wang-meng/film/rebuild-and-cut.sh
