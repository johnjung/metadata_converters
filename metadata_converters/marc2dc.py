#!/usr/bin/env python
"""Usage:
    marc2dc -
"""


import sys
from docopt import docopt
from .converters import MarcToDc


def main():
  options = docopt(__doc__)

  if "-" in options:
    marcxml = sys.stdin.read()

  sys.stdout.write(str(MarcToDc(marcxml)))
  sys.exit()


if __name__=="__main__":
  main()
