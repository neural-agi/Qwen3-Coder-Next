"""Application entry point for foundational runtime bootstrap."""

from qwen3_coder_next.bootstrap.runtime_bootstrap import RuntimeBootstrap

def main() -> int:
    """Start and stop the foundational runtime bootstrap."""

    bootstrap = RuntimeBootstrap.initialize()
    try:
        bootstrap.startup()
    finally:
        bootstrap.shutdown()
    return 0
