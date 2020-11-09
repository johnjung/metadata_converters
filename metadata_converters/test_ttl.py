import sys, unittest
from rdflib import Graph, Literal, URIRef

# https://dldc.lib.uchicago.edu/local/ldr/ssmaps.pdf
# numbering the notes would make them easier to follow.


class TestTTL(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.g_3404181 = Graph()
        self.g_3404181.parse('test_data/3404181.ttl', format='ttl')

        super(TestTTL, self).__init__(*args, **kwargs)

    def test_maps_chisoc_cho(self):
        # dc:description, dc:title, or both are manditory.
        predicate_exists = []
        for predicate in (
            'http://purl.org/dc/elements/1.1/description',
            'http://purl.org/dc/elements/1.1/title'
        ):
            predicate_exists.append(
                (
                    URIRef('ark:61001/b2nw3wm8552h'),
                    URIRef(predicate),
                    None
                ) in self.g_3404181
            )
        self.assertTrue(any(predicate_exists))

        # at least one of dc:coverage, dcterms:spatial, dc:subject,
        # dcterms:temporal, or dc:type are required. 
        predicate_exists = []
        for predicate in (
            'http://purl.org/dc/elements/1.1/coverage',
            'http://purl.org/dc/terms/spatial',
            'http://purl.org/dc/elements/1.1/subject',
            'http://purl.org/dc/terms/temporal',
            'http://purl.org/dc/elements/1.1/type'
        ):
            predicate_exists.append(
                (
                    URIRef('ark:61001/b2nw3wm8552h'),
                    URIRef(predicate),
                    None
                ) in self.g_3404181
            )
        self.assertTrue(any(predicate_exists))

        # dc:language must appear for TEXT objects.
        self.assertTrue(
            (
                URIRef('ark:61001/b2nw3wm8552h'),
                URIRef('http://purl.org/dc/elements/1.1/language'),
                None
            ) in self.g_3404181
        )

        # edm:type must occur.
        self.assertTrue(
            (
                URIRef('ark:61001/b2nw3wm8552h'),
                URIRef('http://www.europeana.eu/schemas/edm/type'),
                None
            ) in self.g_3404181
        )

        # edm:type must be one of the following: TEXT, IMAGE, SOUND,
        # VIDEO or 3D.
        self.assertTrue(
            self.g_3404181.value(
                subject=URIRef('ark:61001/b2nw3wm8552h'),
                predicate=URIRef('http://www.europeana.eu/schemas/edm/type')
            ) in (
                Literal('3D'),
                Literal('IMAGE'),
                Literal('SOUND'),
                Literal('TEXT'),
                Literal('VIDEO')
            )
        )

        # edm:year should occur.
        self.assertTrue(
            (
                URIRef('ark:61001/b2nw3wm8552h'),
                URIRef('http://www.europeana.eu/schemas/edm/year'),
                None
            ) in self.g_3404181
        )

    def test_maps_chisoc_aggregation(self):
        # edm:isShownAt or edm:isShownBy are mandatory.
        predicate_exists = []
        for predicate in (
            'http://www.europeana.eu/schemas/edm/isShownAt',
            'http://www.europeana.eu/schemas/edm/isShownBy'
        ):
            predicate_exists.append(
                (
                    URIRef('ark:61001/b2nw3wm8552h/aggregation'),
                    URIRef(predicate),
                    None
                ) in self.g_3404181
            )
        self.assertTrue(any(predicate_exists))

        # if edm:isShownBy is is used, then edm:object must be supplied. 
        if (
            URIRef('ark:61001/b2nw3wm8552h/aggregation'),
            URIRef('http://www.europeana.eu/schemas/edm/isShownBy'),
            None
        ) in self.g_3404181:
            self.assertTrue(
                (
                    URIRef('ark:61001/b2nw3wm8552h/aggregation'),
                    URIRef('http://www.europeana.eu/schemas/edm/object'),
                    None
                ) in self.g_3404181
            )

        # edm:rights is mandatory.
        self.assertTrue(
            (
                URIRef('ark:61001/b2nw3wm8552h/aggregation'),
                URIRef('http://www.europeana.eu/schemas/edm/rights'),
                None
            ) in self.g_3404181
        )
    
    def test_maps_chisoc_resource_map(self):
        # dcterms:created and dcterms:modified are manditory.
        predicate_exists = []
        for predicate in (
            'http://purl.org/dc/terms/created',
            'http://purl.org/dc/terms/modified'
        ):
            predicate_exists.append(
                (
                    URIRef('ark:61001/b2nw3wm8552h/rem'),
                    URIRef(predicate),
                    None
                ) in self.g_3404181
            )
        self.assertTrue(all(predicate_exists))

    def test_mvol_cho(self):
        raise NotImplementedError

    def test_mvol_aggregation(self):
        raise NotImplementedError

    def test_mvol_resource_map(self):
        raise NotImplementedError


if __name__=="__main__":
    unittest.main()
