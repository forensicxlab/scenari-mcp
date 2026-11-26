#!/bin/bash
# bsdtar already matches archive member patterns; --wildcards is GNU-specific.
# Keep the upstream image/entrypoint intact and preserve argument boundaries.
args=()
strip=()
while (( $# )); do
    case "$1" in
        --wildcards) ;;
        --strip|--strip-components)
            shift
            if (( ! $# )); then
                echo "tar: missing strip-components count" >&2
                exit 2
            fi
            strip=(--strip-components "$1")
            ;;
        --strip=*|--strip-components=*) strip=(--strip-components "${1#*=}") ;;
        *) args+=("$1") ;;
    esac
    shift
done
# GNU accepts bare "zxf" as its first argument; BSD requires a dash when options
# have been moved before it.
if (( ${#args[@]} )) && [[ "${args[0]}" != -* ]]; then
    args[0]="-${args[0]}"
fi
# BSD options must precede member patterns; upstream puts --strip after them.
exec /usr/bin/bsdtar "${strip[@]}" "${args[@]}"
