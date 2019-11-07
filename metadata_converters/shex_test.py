import sys
from pyshex.shex_evaluator import ShExEvaluator
from rdflib import URIRef


if __name__=="__main__":
    with open('G4104-C6-1933-U5-a.ttl') as f:
        rdf = f.read()
    
    with open('shex/uchicago_library_ssmaps.shex') as f:
        shex = f.read()

    # rewrite this:
    # find every subject in the graph.
    # get the shape that corresponds to that subject's type.
    # validate each one in turn. 
    
    for shape, focus in (
                            (
                                URIRef('https://www.lib.uchicago.edu/WebResource'),
                                URIRef('file:///digital_collections/IIIF_Files//social_scientists_maps/G4104-C6-1933-U5-d.tif')
                            ),
                            (
                                URIRef('https://www.lib.uchicago.edu/proxy'),
                                URIRef('file:///digital_collections/IIIF_Files/social_scientists_maps/G4104-C6-1933-U5-d/G4104-C6-1933-U5-d.dc.xml')
                            )
                        ):
        evaluator = ShExEvaluator(
            focus=focus,
            rdf=rdf,
            schema=shex,
            start=shape
        )
        results = evaluator.evaluate()
        for result in results:
            if result.result == False:
                print('ERROR')
                print('FOCUS: {}'.format(result.focus))
                print('START: {}'.format(result.start))
                print('REASON: {}'.format(result.reason.strip()))
                print('')
