"""
TruthLayer LangChain integration.

Install with: pip install truthlayer-sdk[langchain]

Usage:
    from truthlayer.langchain import TruthLayerOutputParser, TruthLayerCallbackHandler
"""

# Lazy re-exports from the integrations module.
# This allows `from truthlayer.langchain import TruthLayerOutputParser`
# after installing with `pip install truthlayer-sdk[langchain]`.

import importlib.util
import os
import sys

# The actual implementation lives in integrations/langchain/truthlayer_langchain.py
# at the repo root. When installed as a package, we need to handle both contexts:
# 1. Development (running from repo root)
# 2. Installed package (this file is inside site-packages/truthlayer/langchain/)

_INTEGRATION_LOADED = False


def _load_integration():
    """Attempt to load the LangChain integration module."""
    global _INTEGRATION_LOADED

    if _INTEGRATION_LOADED:
        return

    try:
        # Try repo-structure import first (development mode)
        _repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        _integration_path = os.path.join(_repo_root, "integrations", "langchain", "truthlayer_langchain.py")

        if os.path.exists(_integration_path):
            spec = importlib.util.spec_from_file_location(
                "truthlayer._langchain_impl", _integration_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Re-export public symbols into this namespace
            _current = sys.modules[__name__]
            for name in [
                "TruthLayerOutputParser",
                "TruthLayerCallbackHandler",
                "VerifiedOutput",
                "HallucinationDetectedError",
            ]:
                if hasattr(module, name):
                    setattr(_current, name, getattr(module, name))

            _INTEGRATION_LOADED = True
        else:
            raise ImportError(
                "LangChain integration not found. "
                "Ensure integrations/langchain/ is present in the repo."
            )
    except ImportError as e:
        raise ImportError(
            f"Failed to load TruthLayer LangChain integration: {e}. "
            "Install with: pip install truthlayer-sdk[langchain]"
        ) from e


# Eagerly load on import
_load_integration()

__all__ = [
    "TruthLayerOutputParser",
    "TruthLayerCallbackHandler",
    "VerifiedOutput",
    "HallucinationDetectedError",
]
