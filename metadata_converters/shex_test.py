import rdflib, re, sys
from pyshex.shex_evaluator import ShExEvaluator
from rdflib.namespace import RDF


if __name__=="__main__":
    # rdf = sys.stdin.read()
    
    with open('shex/uchicago_library_ssmaps.shex') as f:
        shex = f.read()

    g = rdflib.Graph()
    g.parse(sys.argv[1], format='turtle')

    subjects = {}
    for s, _, o in g.triples((None, RDF.type, None)):
        # take the beginning part off and add <https://www.lib.uchicago.edu/>
        subjects[s] = re.sub('^.*/', 'https://www.lib.uchicago.edu/', o)

    for focus, shape in subjects.items():
        evaluator = ShExEvaluator(
            focus=focus,
            rdf=g,
            schema=shex,
            start=shape
        )
        sys.exit()
        results = evaluator.evaluate()
        for result in results:
            if result.result == False:
                print('ERROR')
                print('FOCUS: {}'.format(result.focus))
                print('START: {}'.format(result.start))
                print('REASON: {}'.format(result.reason.strip()))
                print('')
