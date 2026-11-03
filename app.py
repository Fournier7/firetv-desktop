"""Ponto de entrada usado pelo empacotamento (PyInstaller)."""
from firetv.main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
