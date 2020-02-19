#!/usr/bin/env python
"""Usage:
    marc2dc [--socscimaps] -
"""

import sys
import xml.etree.ElementTree as ElementTree
from docopt import docopt
from . import SocSciMapsMarcXmlToDc

ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')

def main():
    options = docopt(__doc__)

    marcxml_str = sys.stdin.read()
    if options['--socscimaps']:
        records = ElementTree.fromstring(
            marcxml_str
        ).findall('{http://www.loc.gov/MARC21/slim}record')

	# catch single records if they are wrapped in a <collection> element or
	# if the <record> element is at the top level.
        if len(records) == 0:
            sys.stdout.write(
                str(
                    SocSciMapsMarcXmlToDc(
                        '<collection>{}</collection>'.format(marcxml_str)
                    )
                )
            )
        elif len(records) == 1:
            sys.stdout.write(
                str(
                    SocSciMapsMarcXmlToDc(
                        '<collection>{}</collection>'.format(
                            ElementTree.tostring(records[0], 'utf-8', method='xml').decode('utf-8')
                        )
                    )
                )
            )
        else:
            metadata = ElementTree.Element('metadata')
            for record in records:
                metadata.append(
                    SocSciMapsMarcXmlToDc(
                        '<collection>{}</collection>'.format(
                            ElementTree.tostring(record, 'utf-8', method='xml').decode('utf-8')
                        )
                    )._asxml()
                )
            sys.stdout.write(ElementTree.tostring(metadata, 'utf-8', method='xml').decode('utf-8'))
    else:
        raise NotImplementedError

if __name__ == "__main__":
    main()
