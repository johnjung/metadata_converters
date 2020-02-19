#!/usr/bin/env python
"""Convert MARCXML to Facebook Open Graph"""

import sys
from . import MarcXmlToOpenGraph

def main():
    sys.stdout.write(str(MarcXmlToOpenGraph(sys.stdin.read())))

if __name__ == "__main__":
    main()
