#!/usr/bin/env python
"""Usage:
    mvol_tools [--to-dc] -
    mvol_tools [--to-schema-dot-org] -
"""


import sys
from docopt import docopt
from converters import MarcToDc, MarcXmlToSchemaDotOrg

if __name__=="__main__":

  options = docopt(__doc__)

  if "-" in options:
    marcxml = sys.stdin.read()

  if options["--to-dc"]:
    sys.stdout.write(str(MarcToDc(marcxml)))
    sys.exit()
  elif options["--to-schema-dot-org"]:
    sys.stdout.write(str(MarcXmlToSchemaDotOrg(marcxml)))
    sys.exit()
