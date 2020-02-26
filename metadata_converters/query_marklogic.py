#!/usr/bin/env python
"""Usage:
    query_marklogic <collection>
"""

import json, os, requests, sys
from docopt import docopt
from requests.auth import HTTPBasicAuth

# to delete all the triples from a collection, use the following curl
# command:
# curl --anyauth --user user:password -X DELETE http://server:port/v1/graphs?graph=collection

def main():
    options = docopt(__doc__)

    r = requests.get(
        auth=HTTPBasicAuth(
            os.environ['MARKLOGIC_LDR_USER'],
            os.environ['MARKLOGIC_LDR_PASSWORD']
        ),  
        headers={
            'Content-type': 'text/turtle'
        },  
        params={
            'query': 'select ?s ?p ?o from <{}> where {{ ?s ?p ?o . }}'.format(
                options['<collection>']
            )
        },
        url='http://marklogic.lib.uchicago.edu:8008/v1/graphs/sparql'
    )

    for r in json.loads(
        r.content.decode('utf-8')
    )['results']['bindings']:
        if r['o']['type'] == 'uri':
            formatted_string = '<{}> <{}> <{}> .'
        elif 'datatype' in r['o']:
            if r['o']['datatype'] == 'http://www.w3.org/2001/XMLSchema#integer':
                formatted_string = '<{}> <{}> {} .'
            elif r['o']['datatype'] == 'http://www.w3.org/2001/XMLSchema#dateTime':
                formatted_string = '<{}> <{}> "{}" .'
            else:
                raise NotImplementedError
        elif r['o']['type'] == 'literal':
            formatted_string = '<{}> <{}> "{}" .'
        else:
            raise NotImplementedError

        print(formatted_string.format(
            r['s']['value'], 
            r['p']['value'],
            r['o']['value']
        ))

if __name__=="__main__":
    main()
