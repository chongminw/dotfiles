# Inputs: BARC_PROXY_* from settings.bash. Outputs: proxy function; exports only on demand.
# Optional command: curl, only for an explicit HTTP proxy request.
: "${BARC_PROXY_HOST:=127.0.0.1}"
: "${BARC_PROXY_PORT:=7889}"
: "${BARC_PROXY_NO_PROXY:=localhost,127.0.0.1,::1,192.168.0.0/16}"
: "${BARC_PROXY_TEST_URL:=https://github.com}"

_barc_proxy_validate() {
    if [[ ! $BARC_PROXY_HOST =~ ^[a-zA-Z0-9._:-]+$ ||
          ! $BARC_PROXY_PORT =~ ^[0-9]{1,5}$ ]]; then
        builtin printf 'proxy: invalid host or port\n' >&2
        return 2
    fi
    if (( 10#$BARC_PROXY_PORT < 1 || 10#$BARC_PROXY_PORT > 65535 )); then
        builtin printf 'proxy: port must be between 1 and 65535\n' >&2
        return 2
    fi
}

_barc_proxy_authority() {
    if [[ $BARC_PROXY_HOST == *:* ]]; then
        builtin printf '[%s]:%s' "$BARC_PROXY_HOST" "$((10#$BARC_PROXY_PORT))"
    else
        builtin printf '%s:%s' "$BARC_PROXY_HOST" "$((10#$BARC_PROXY_PORT))"
    fi
}

proxy() {
    local _barc_p_action=${1:-} _barc_p_authority _barc_p_code _barc_p_rc
    (( $# <= 1 )) || { builtin printf 'Usage: proxy {on|off|status|test}\n' >&2; return 2; }
    case $_barc_p_action in
        off|of)
            unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY
            builtin printf 'proxy disabled\n'
            return 0 ;;
        on|status|st|test|ts) ;;
        *) builtin printf 'Usage: proxy {on|off|status|test}\n' >&2; return 2 ;;
    esac
    _barc_proxy_validate || return "$?"
    _barc_p_authority=$(_barc_proxy_authority)
    case $_barc_p_action in
        on)
            export http_proxy=http://$_barc_p_authority https_proxy=http://$_barc_p_authority
            export HTTP_PROXY=$http_proxy HTTPS_PROXY=$https_proxy
            export all_proxy=socks5h://$_barc_p_authority ALL_PROXY=socks5h://$_barc_p_authority
            export no_proxy=$BARC_PROXY_NO_PROXY NO_PROXY=$BARC_PROXY_NO_PROXY
            builtin printf 'proxy environment enabled: %s\n' "$http_proxy" ;;
        status|st)
            builtin printf 'Configured endpoint: http://%s\n' "$_barc_p_authority"
            builtin printf 'Environment: http_proxy=%s https_proxy=%s all_proxy=%s\n' \
                "${http_proxy:-<unset>}" "${https_proxy:-<unset>}" "${all_proxy:-<unset>}"
            builtin printf 'Bypass list: %s\n' "${no_proxy:-<unset>}"
            builtin printf 'Endpoint not probed. Use proxy test to verify an explicit proxy request.\n' ;;
        test|ts)
            case $BARC_PROXY_TEST_URL in
                http://?*|https://?*) ;;
                *) builtin printf 'proxy: test URL must use HTTP or HTTPS\n' >&2; return 2 ;;
            esac
            command -v curl >/dev/null 2>&1 || { builtin printf 'proxy: curl is unavailable\n' >&2; return 127; }
            # -q ignores .curlrc; empty noproxy prevents inherited bypass lists.
            if _barc_p_code=$(command curl -q --silent --show-error --output /dev/null \
                --proxy "http://$_barc_p_authority" --noproxy '' \
                --proto '=http,https' --proto-redir '=http,https' --location \
                --connect-timeout 5 --max-time 15 --write-out '%{http_code}' \
                --url "$BARC_PROXY_TEST_URL"); then
                case $_barc_p_code in
                    2??|3??) builtin printf 'Proxy request succeeded: HTTP %s via %s\n' "$_barc_p_code" "$_barc_p_authority" ;;
                    *) builtin printf 'Proxy request returned HTTP %s via %s\n' "$_barc_p_code" "$_barc_p_authority" >&2; return 1 ;;
                esac
            else
                _barc_p_rc=$?
                builtin printf 'Proxy request failed: curl=%s via %s\n' "$_barc_p_rc" "$_barc_p_authority" >&2
                return "$_barc_p_rc"
            fi ;;
    esac
}
return 0
