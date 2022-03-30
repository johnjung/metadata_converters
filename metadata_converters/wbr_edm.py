#!/usr/bin/env python
"""Usage: wbr_edm <ark> <original-name>
"""

import hashlib, requests, sys
from docopt import docopt
from PIL import Image
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF 

Image.MAX_IMAGE_PIXELS = 1000000000

ARK     = Namespace('https://www.lib.uchicago.edu/ark:61001/')
EDM     = Namespace('http://www.europeana.eu/schemas/edm/')
EBUCORE = Namespace('https://www.ebu.ch/metadata/ontologies/ebucore/')
PREMIS3 = Namespace('http://www.loc.gov/premis/rdf/v3/')

if __name__ == "__main__":
    options = docopt(__doc__)

    noid = options['<ark>'].replace('ark:61001/', '').replace('ark:/61001/', '')

    graph = Graph()
    for prefix, ns in (('ebucore', EBUCORE), ('edm', EDM),
                       ('premis', PREMIS3)):
        graph.bind(prefix, ns)

    r = requests.get('https://ocfl.lib.uchicago.edu:/{}/file.tif'.format(options['<ark>']))

    wbr = ARK['{}/file.tif'.format(noid)]

    graph.add((wbr, RDF.type,                 EDM.WebResource))
    graph.add((wbr, EBUCORE.hasMimeType,      Literal('image/tiff')))

    fixity = BNode()
    graph.add((wbr, PREMIS3.fixity,           fixity))
    graph.add((fixity,   RDF.type,            URIRef('https://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/sha512')))
    graph.add((fixity,   RDF.value,           Literal(hashlib.sha512(r.content).hexdigest())))

    graph.add((wbr, PREMIS3.compositionLevel, Literal(0)))
    graph.add((wbr, PREMIS3.originalName,     Literal(options['<original-name>'])))
    graph.add((wbr, PREMIS3.size,             Literal(len(r.content))))

    sys.stdout.write(
        graph.serialize(format='turtle', base='https://www.lib.uchicago.edu/ark:61001/')
    )
