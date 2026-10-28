# Inputs: optional system bash-completion. Outputs: completion functions and Readline bindings.
# Load before alias modules; missing completion and unavailable bind are nonfatal.

# 避免重复加载 bash-completion。
if ! declare -p BASH_COMPLETION_VERSINFO >/dev/null 2>&1; then
    if [[ -r /usr/share/bash-completion/bash_completion ]]; then
        # shellcheck source=/usr/share/bash-completion/bash_completion
        source /usr/share/bash-completion/bash_completion
    elif [[ -r /etc/bash_completion ]]; then
        # shellcheck source=/etc/bash_completion
        source /etc/bash_completion
    fi
fi

# 补全行为。
builtin bind 'set completion-ignore-case on' 2>/dev/null || true
builtin bind 'set show-all-if-ambiguous on' 2>/dev/null || true
builtin bind 'set completion-map-case on' 2>/dev/null || true
builtin bind 'set mark-symlinked-directories on' 2>/dev/null || true

# 历史搜索。
builtin bind '"\e[A": history-search-backward' 2>/dev/null || true
builtin bind '"\e[B": history-search-forward' 2>/dev/null || true

# 单词移动。
builtin bind '"\e[1;5C": forward-word' 2>/dev/null || true
builtin bind '"\e[1;5D": backward-word' 2>/dev/null || true
builtin bind '"\e[1;3C": forward-word' 2>/dev/null || true
builtin bind '"\e[1;3D": backward-word' 2>/dev/null || true

# 编辑快捷键。
builtin bind '"\C-w": backward-kill-word' 2>/dev/null || true
builtin bind '"\C-_": undo' 2>/dev/null || true
builtin bind '"\C-l": clear-screen' 2>/dev/null || true
