#!/usr/bin/env python
"""Convert MARCXML to Twitter Card"""

import sys
from . import MarcXmlToTwitterCard

def main():
    sys.stdout.write(str(MarcXmlToTwitterCard(sys.stdin.read())))

if __name__ == "__main__":
    main()
