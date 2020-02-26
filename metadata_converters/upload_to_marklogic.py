#!/usr/bin/env python
"""Usage:
    upload_to_marklogic <graph> -
"""

import os, requests, sys
from docopt import docopt
from requests.auth import HTTPBasicAuth

def main():
    options = docopt(__doc__)

    r = requests.post(
        auth=HTTPBasicAuth(
            os.environ['MARKLOGIC_LDR_USER'],
            os.environ['MARKLOGIC_LDR_PASSWORD']
        ),  
        data=sys.stdin.buffer.read(),
        headers={
            'Content-type': 'text/turtle'
        },  
        params={
            'graph': options['<graph>']
        },  
        url=os.environ['MARKLOGIC_LDR_URL']
    )   

    sys.stdout.write('{}\n'.format(r.status_code))
    sys.stdout.write('{}\n'.format(r.content.decode('utf-8')))

if __name__=="__main__":
    main()
