#!/usr/bin/env python
"""Usage:
    marc2schemadotorg -
    marc2schemadotorg -f <path>
Options:
  -h --help     Show this screen.
  -f --file     File path to make manifest from
  -             Take input from the terminal
"""


import sys
from docopt import docopt
from . import MarcXmlToSchemaDotOrg

def main():
	options = docopt(__doc__)

	if options['--file']:
		with open(options['<path>'], 'r') as file:
			marcxml = file.read()
	elif options['-']:
		marcxml = sys.stdin.read()
	else:
		sys.exit()

	sys.stdout.write(str(MarcXmlToSchemaDotOrg(marcxml)))
	sys.exit()

if __name__ == "__main__":
    main()
