#!/usr/bin/env python

import copy, json, re, sys
import xml.etree.ElementTree as ElementTree
from classes import SocSciMapsMarcXmlToDc


if __name__=='__main__':
    ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')
    for record in ElementTree.fromstring(
        sys.stdin.read()
    ).findall('{http://www.loc.gov/MARC21/slim}record'):
        sys.stdout.write(
            str(
                SocSciMapsMarcXmlToDc(
                    '<collection>{}</collection>'.format(
                        ElementTree.tostring(record, 'utf-8', method='xml').decode('utf-8')
                    )
                )
            )
        )
        sys.stdout.write('\n')
        sys.exit()
