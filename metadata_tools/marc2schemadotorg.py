#!/usr/bin/env python
"""Usage:
    marc2schemadotorg -
"""


import sys
from docopt import docopt
from .converters import MarcXmlToSchemaDotOrg


def main():
  options = docopt(__doc__)

  if "-" in options:
    marcxml = sys.stdin.read()

  sys.stdout.write(str(MarcXmlToSchemaDotOrg(marcxml)))
  sys.exit()


if __name__=="__main__":
  main()
