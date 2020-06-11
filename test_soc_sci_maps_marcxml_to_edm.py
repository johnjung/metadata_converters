# -*- coding: utf-8 -*-
import re, sys, unittest
from metadata_converters import SocSciMapsMarcXmlToEDM
from pymarc import MARCReader
from rdflib import Literal, URIRef
from rdflib.namespace import DC, DCTERMS


class TestSocSciMapsMarcXmlToEDM(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mrc = {}
        for m in ('3451312', '5999566', '7368094', '7641168'):
            with open('./test_data/{}.mrc'.format(m), 'rb') as fh:
                reader = MARCReader(fh)
                for record in reader:
                    self.mrc[m] = record

        self.edm = {}
        for d, p in (('7641168', '3451312'), ('5999566', '7368094')):
            k = '{},{}'.format(d, p)
            self.edm[k] = SocSciMapsMarcXmlToEDM(
                self.mrc[d],
                self.mrc[p],
                []
            )
            self.edm[k].build_item_triples()

        self.agg = {
            '7641168,3451312': URIRef('/aggregation/digital_collections/IIIF_Files/maps/chisoc/G4104-C6-2W9-1920z-U5'),
            '5999566,7368094': URIRef('/aggregation/digital_collections/IIIF_Files/maps/chisoc/G4104-C6E625-1920-S5')
        }

        self.cho = {
            '7641168,3451312': URIRef('/digital_collections/IIIF_Files/maps/chisoc/G4104-C6-2W9-1920z-U5'),
            '5999566,7368094': URIRef('/digital_collections/IIIF_Files/maps/chisoc/G4104-C6E625-1920-S5')
        }

        self.rem = {
            '7641168,3451312': URIRef('/rem/digital_collections/IIIF_Files/maps/chisoc/G4104-C6-2W9-1920z-U5'),
            '5999566,7368094': URIRef('/rem/digital_collections/IIIF_Files/maps/chisoc/G4104-C6E625-1920-S5')
        }

    def test_agg_aggregated_cho(self):
        """edm:aggregatedCHO should point to the CHO."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.agg[ids],
                predicate=URIRef('http://www.europeana.eu/schemas/edm/aggregatedCHO')
            ),
            self.cho[ids]
        )

    def test_agg_created(self):
        """dcterms:created will match "[YYYY]-[MM]-[DD]T[HH]:[MM]:[SS]"^^xsd:dateTime;"""

        ids = '7641168,3451312'

        self.assertTrue(
            re.match(
                '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d*$',
                str(
                    self.edm[ids].graph.value(
                        subject=self.agg[ids],
                        predicate=URIRef('http://purl.org/dc/terms/created')
                    )
                )
            ) != None
        )

    def test_agg_data_provider(self):
        """edm:dataProvider is the literal string 
           'University of Chicago Library'"""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.agg[ids],
                predicate=URIRef('http://www.europeana.eu/schemas/edm/dataProvider')
            ),
            Literal('The University of Chicago Library')
        )

    def test_agg_is_described_by(self):
        """ore:isDescribedBy links to the resource map. It's reciprocal with
           ore:describes."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.agg[ids],
                predicate=URIRef('http://www.openarchives.org/ore/terms/isDescribedBy')
            ),
            self.rem[ids]
        )

    def test_agg_modified(self):
        """dcterms:modified will match "[YYYY]-[MM]-[DD]T[HH]:[MM]:[SS]"^^xsd:dateTime;"""

        ids = '7641168,3451312'

        self.assertTrue(
            re.match(
                '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d*$',
                str(
                    self.edm[ids].graph.value(
                        subject=self.agg[ids],
                        predicate=URIRef('http://purl.org/dc/terms/modified')
                    )
                )
            ) != None
        )

    def test_agg_provider(self):
        """edm:provider is the literal string 
           'University of Chicago Library'"""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.agg[ids],
                predicate=URIRef('http://www.europeana.eu/schemas/edm/provider')
            ),
            Literal('The University of Chicago Library')
        )

    def test_agg_rights(self):
        """edm:rights is the URI
           https://rightsstatements.org/page/InC/1.0/?language=en"""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.agg[ids],
                predicate=URIRef('http://www.europeana.eu/schemas/edm/rights')
            ),
            URIRef('https://rightsstatements.org/page/InC/1.0/?language=en')
        )

    def test_cho_classification_lcc(self):
        """get bf:ClassificationLcc from MARC to DC conversion."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://id.loc.gov/ontologies/bibframe/ClassificationLcc')
            ),
            Literal('G4104.C6:2W9 1920z .U5')
        )

    def test_cho_creator(self):
        """get dc:creator from the MARC to DC conversion."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/creator')
            ),
            Literal('University of Chicago. Department of Sociology')
        )

    def test_cho_current_location(self): 
        """edm:currentLocation is the literal string 
           'Map Collection Reading Room (Room 370)'"""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://www.europeana.eu/schemas/edm/currentLocation')
            ),
            Literal('Map Collection Reading Room (Room 370)')
        )

    def test_cho_date(self):
        """dc:date, pull from 260$c or 264$c."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/date')
            ),
            Literal('1920/1929')
        )

    def test_cho_description(self):
        """get dc:description from MARC to DC conversion."""

        ids = '7641168,3451312'

        descriptions_set = set()
        for o in self.edm[ids].graph.objects(
            subject=self.cho[ids],
            predicate=URIRef('http://purl.org/dc/elements/1.1/description')
        ):
            descriptions_set.add(o)

        self.assertEqual(
            descriptions_set, 
            set((
                Literal('Blue line print.'),
                Literal('Shows residential area, vacant area, commercial frontage, railroad property, and transit lines.'),
                Literal('Master and use copy. Digital master created according to Benchmark for Faithful Reproductions of Monographs and Serials, Version 1. Digital Library Federation, December 2002. http://www.diglib.org/standards/bmarkfin.htm')
            ))
        )

    def test_cho_format(self):
        """get dc:format from MARC to DC conversion."""

        ids = '7641168,3451312'

        formats_set = set()
        for o in self.edm[ids].graph.objects(
            subject=self.cho[ids],
            predicate=URIRef('http://purl.org/dc/elements/1.1/format')
        ):
            formats_set.add(o)

        self.assertEqual(
            formats_set, 
            set((
                Literal('1 map'),
                Literal('45 x 62 cm'),
                Literal('Scale [ca. 1:8,000]')
            ))
        )

    def test_cho_has_format(self):
        """get dcterms:hasFormat from MARC to DC conversion."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/terms/hasFormat')
            ),
            Literal('Print version')
        )

    def test_cho_identifier(self):
        """get dc:identifier from MARC to DC conversion."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/identifier')
            ),
            Literal('http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-2W9-1920z-U5')
        )

    def test_cho_language(self):
        """get dc:language from MARC to DC converter."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/language')
            ),
            Literal('English')
        )

    def test_cho_local(self):
        """get bf:Local from MARC to DC converter."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://id.loc.gov/ontologies/bibframe/Local')
            ),
            Literal('http://pi.lib.uchicago.edu/1001/cat/bib/3451312')
        )

    def test_cho_publisher(self):
        """get dc:publisher from MARC to DC converter."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/publisher')
            ),
            Literal('Dept. of Sociology')
        )

    def test_cho_spatial(self):
        """get dcterms:spatial from MARC to DC converter."""

        ids = '5999566,7368094'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/terms/spatial')
            ),
            Literal('Illinois -- Chicago')
        )

    def test_cho_subject(self):
        """get dc:subject from MARC to DC converter."""

        ids = '5999566,7368094'

        subjects_set = set()
        for s in self.edm[ids].graph.objects(
            subject=self.cho[ids],
            predicate=URIRef('http://purl.org/dc/elements/1.1/subject')
        ):
            subjects_set.add(s)

        self.assertEqual(
            subjects_set,
            set((
                Literal('Crime'),
                Literal('Criminals')
            ))
        )

    def test_cho_title(self):
        """get dc:title from MARC to DC converter."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/title')
            ),
            Literal('Woodlawn Community /')
        )

    def test_cho_type(self):
        """get dc:type from MARC to DC converter."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/dc/elements/1.1/type')
            ),
            Literal('Maps')
        )

    def test_cho_what(self):
        """get erc:what from MARC to DC converter dc:title."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/kernel/elements/1.1/what')
            ),
            Literal('Woodlawn Community /')
        )

    def test_cho_when(self):
        """get erc:when from 260$c or 264$c, should match dc:date."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/kernel/elements/1.1/when')
            ),
            Literal('1920/1929')
        )

    def test_who(self):
        """get erc:who from MARC to DC converter dc:creator."""

        ids = '7641168,3451312'

        self.assertEqual(
            self.edm[ids].graph.value(
                subject=self.cho[ids],
                predicate=URIRef('http://purl.org/kernel/elements/1.1/who')
            ),
            Literal('University of Chicago. Department of Sociology')
        )

    # def test_where(self):
    #     # the URI for the edm:ProvidedCHO (i.e., the subject of these assertions) -> erc:where
    #     # erc:where <[NOID]/[path/to/providedCHO]>;
    #     raise NotImplementedError

    # def test_year(self):
    #     # Edm: year [ copy dcterms:dateCopyrighted ]
    #     # JEJ switched the triple above from edm:year [260/264 $c subfield from MARCXML (whichever is populated)];
    #     raise NotImplementedError


if __name__ == '__main__':
    unittest.main()
