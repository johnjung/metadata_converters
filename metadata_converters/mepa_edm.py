#!/usr/bin/env python
"""Usage: mepa_edm <work_refid>
"""

import copy
import datetime
import urllib.parse
import sys
import xml.etree.ElementTree as ElementTree
from docopt import docopt
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, DC, DCTERMS, XSD
from classes import BASE, BF, EDM, ERC, MADSRDF, MIX, OAI, ORE, PREMIS, PREMIS2, PREMIS3, VRA
from classes import REPOSITORY_AGG, REPOSITORY_CHO, REPOSITORY_REM 
from classes import DIGCOL_AGG, DIGCOL_CHO, DIGCOL_REM 
from classes import DigitalCollectionToEDM


class MepaToEDM(DigitalCollectionToEDM):
    """A class to convert MEPA's Filemaker database to EDM."""

    def __init__(self, vra, noid):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        super(MepaToEDM, self).__init__()
        self.graph.bind('vra', VRA)
        self.graph.bind('base', 'ark:/61001/')

        self.vra = vra
        self.noid = noid

        self.MEPA = Namespace('https://repository.lib.uchicago.edu/digital_collections/mepa/')
        self.MEPA_AGG = self.MEPA['aggregation']
        self.MEPA_CHO = self.MEPA['']
        self.MEPA_REM = self.MEPA['rem']

        self.ARK = Namespace('ark:/61001/')
        self.work_agg = self.ARK['aggregation']
        self.work_cho = self.ARK['']
        self.work_rem = self.ARK['rem']
        self.work_wbr = URIRef('http://example.org/')

        self.RECTO = Namespace('ark:/61001/Recto/')
        self.recto_agg = self.RECTO['aggregation']
        self.recto_cho = self.RECTO['']
        self.recto_rem = self.RECTO['rem']
        self.recto_wbr = URIRef(
            'https://iiif-server-dev.lib.uchicago.edu/{}'.format(
                urllib.parse.quote('ark:/61001/{}/00000001'.format(self.noid), safe='')
            )
        )

        self.VERSO = Namespace('ark:/61001/Verso/')
        self.verso_agg = self.VERSO['aggregation']
        self.verso_cho = self.VERSO['']
        self.verso_rem = self.VERSO['rem']
        self.verso_wbr = URIRef(
            'https://iiif-server-dev.lib.uchicago.edu/{}'.format(
                urllib.parse.quote('ark:/61001/{}/00000001'.format(self.noid), safe='')
            )
        )

    def build_work_triples(self):
        """Add triples for an individual work.

        Side Effect:
            Add triples to self.graph
        """
        # aggregation for the item.
        self.agg_graph(
            self.work_agg,
            self.work_cho,
            self.work_rem,
            self.work_wbr
        )

        self._build_cho()

        # resource map for the item.
        self.rem_graph(
            self.work_agg,
            self.work_rem,
            self.now
        )

        # connect the item to its collection.
        self.graph.add((self.MEPA_CHO, DCTERMS.hasPart, self.work_cho))

    def _build_cho(self):
        """The cultural herigate object is the map itself. 

        This method adds triples that describe the cultural heritage object.
        Note- for MEPA, a file.dc.xml is not produced. 

        Args:
            agg (URIRef): aggregation 
            cho (URIRef): cultural heritage object

        Side Effect:
            Add triples to self.graph
        """

        self.graph.add((self.work_cho, RDF.type, EDM.ProvidedCHO))

        # dc:alternative
        for e in self.vra.findall(
            ".//vra:titleSet/vra:title[@pref='false']",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, DC.alternative, Literal(e.text.strip())))

        # dc:creator
        for e in self.vra.findall(
            ".//vra:agentSet/vra:agent/vra:name",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            o = None
            try:
                assert e.attrib['vocab'] == 'ULAN'
                o = URIRef('http://vocab.getty.edu/ulan/{}'.format(e.attrib['refid'].strip()))
            except (AssertionError, AttributeError, KeyError):
                try:
                    o = Literal(e.find('name').text.strip())
                except KeyError:
                    pass
            if o:
                self.graph.add((self.work_cho, DC.creator, o))
                self.graph.add((self.work_cho, ERC.who, o))

        # dc:extent
        for e in self.vra.findall(
            ".//vra:measurementsSet/vra:display",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, DC.extent, Literal(e.text.strip())))

        # dc:format
        for e in self.vra.findall(
            ".//vra:techniqueSet/vra:technique",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            if e.attrib['vocab'] == 'AAT':
                self.graph.add((
                    self.work_cho, 
                    URIRef('http://purl.org/dc/elements/1.1/format'), 
                    URIRef('http://vocab.getty.edu/aat/{}'.format(e.attrib['refid'].strip()))
                ))
            else:
                raise NotImplementedError

        # dc:identifier
        self.graph.add((self.work_cho, DC.identifier, URIRef('http://example.org')))

        # dc:language
        languages = set()
        for e in self.vra.findall(
            ".//vra:titleSet/vra:title",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            try:
                languages.add(e.attrib['{http://www.w3.org/XML/1998/namespace}lang'].strip())
            except KeyError:
                pass
        for l in languages: 
            self.graph.add((self.work_cho, DC.language, Literal(l)))

        # dc:rights
        self.graph.add((self.work_cho, DC.rights, Literal('A text string to be determined')))

        # dc:subject
        for e in self.vra.findall(
            './/vra:subjectSet/vra:subject/vra:term',
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            if e.attrib['vocab'] == 'LCNAF':
                o = URIRef('http://id.loc.gov/authorities/names/{}'.format(e.attrib['refid'].strip()))
            elif e.attrib['vocab'] == 'FAST':
                o = URIRef('http://id.worldcat.org/fast/{}'.format(e.attrib['refid'].strip()))
            elif e.attrib['vocab'] == 'DBPedia':
                o = URIRef(e.attrib['refid'].strip())
            else:
                raise NotImplementedError
            self.graph.add((self.work_cho, DC.subject, o))

        # dc:type
        self.graph.add((self.work_cho, DC.type, Literal('Image')))

        # dc:title
        for e in self.vra.findall(
            ".//vra:titleSet/vra:title[@pref='true']",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            o = Literal(e.text.strip())
            self.graph.add((self.work_cho, DC.title, o))
            self.graph.add((self.work_cho, ERC.what, o))

        # dcterms:hasPart
        self.graph.add((self.work_cho, DCTERMS.hasPart, self.recto_cho))
        self.graph.add((self.work_cho, DCTERMS.hasPart, self.verso_cho))

        # dcterms:isPartOf
        self.graph.add((self.work_cho, DCTERMS.isPartOf, URIRef('http://example.org/')))

        # dcterms:spatial
        for e in self.vra.findall(
            './/vra:locationSet/vra:location[@type="creation"]/vra:name',
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            if e.attrib['vocab'] == 'TGN':
                self.graph.add((
                    self.work_cho, 
                    DCTERMS.spatial, 
                    URIRef('http://vocab.getty.edu/tgn/{}'.format(e.attrib['refid'].strip()))
                ))
            else:
                raise NotImplementedError

        # dcterms:temporal
        for e in self.vra.findall(
            ".//vra:dateSet/vra:display",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, DCTERMS.temporal, Literal(e.text.strip())))

        # edm:date
        for e in self.vra.findall(
            ".//vra:dateSet/vra:date/vra:earliestDate",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            o = Literal(int(e.text))
            self.graph.add((self.work_cho, EDM.date, o))
            self.graph.add((self.work_cho, ERC.when, o))

        # edm:type
        self.graph.add((self.work_cho, EDM.type, Literal('IMAGE')))

        # erc:where
        self.graph.add((self.work_cho, ERC.where, self.work_cho))

        # vra:continent
        for e in self.vra.findall(
            "./vra:work/vra:locationSet/vra:location[@type='creation']/vra:name[@extent='continent']",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, VRA.Continent, Literal(e.text.strip())))

        # vra:country
        for e in self.vra.findall(
            "./vra:work/vra:locationSet/vra:location[@type='creation']/vra:name[@extent='nation']",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, VRA.Country, Literal(e.text.strip())))

        # vra:state
        for extent in ('province', 'region'):
            for e in self.vra.findall(
                "./vra:work/vra:locationSet/vra:location[@type='creation']/vra:name[@extent='{}']".format(extent),
                {'vra': 'http://www.vraweb.org/vracore4.htm'}
            ):
                self.graph.add((self.work_cho, VRA.State, Literal(e.text.strip())))

        # vra:city
        for e in self.vra.findall(
            "./vra:work/vra:locationSet/vra:location[@type='creation']/vra:name[@extent='inhabited place']",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((self.work_cho, VRA.City, Literal(e.text.strip())))

        # site or building never exists.

    def build_recto_verso_triples(self):
        # aggregation for the item.
        self.agg_graph(
            self.recto_agg,
            self.recto_cho,
            self.recto_rem,
            self.recto_wbr
        )
        self.agg_graph(
            self.verso_agg,
            self.verso_cho,
            self.verso_rem,
            self.verso_wbr
        )

        # cho for this item.
        self._build_recto_verso_cho(
            self.recto_agg,
            self.recto_cho,
            self.recto_rem,
            'Recto'
        )
        self._build_recto_verso_cho(
            self.verso_agg,
            self.verso_cho,
            self.verso_cho,
            'Verso'
        )

        # resource map for the item.
        self.rem_graph(
            self.recto_agg, 
            self.recto_rem,
            self.now
        )
        self.rem_graph(
            self.verso_agg, 
            self.verso_rem,
            self.now
        )

    def _build_recto_verso_cho(self, agg, cho, rem, description_prefix):
        # dc.description
        work_id = self.vra.find(
            './/vra:work', 
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ).attrib['id'].strip()

        for p, o in ((RDF.type,       EDM.ProvidedCHO),
                     (DC.description, Literal('{} {}'.format(description_prefix, work_id))),
                     (DC.rights,      Literal('A text string to be determined.')),
                     (DC.type,        Literal('Image')),
                     (DCTERMS.type,   self.work_cho),
                     (EDM.type,       Literal('IMAGE'))):
            self.graph.add((cho, p, o))

        # dc:language
        languages = set()
        for e in self.vra.findall(
            ".//vra:titleSet/vra:title",
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            try:
                languages.add(e.attrib['{http://www.w3.org/XML/1998/namespace}lang'].strip())
            except KeyError:
                pass
        for l in languages: 
            self.graph.add((cho, DC.language, Literal(l)))

        # vra.inscription
        for e in self.vra.findall(
            './/vra:inscriptionSet/vra:display',
            {'vra': 'http://www.vraweb.org/vracore4.htm'}
        ):
            self.graph.add((cho, VRA.inscription, Literal(e.text.strip())))


    @classmethod
    def build_mepa_collection_triples(self):
        """Add triples for MEPA, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation
        self.agg_graph(self.MEPA_AGG, self.MEPA_CHO, self.MEPA_REM, MEPA_WBR)

        # cultural heritage object
        for p, o in ((RDF.type,  EDM.ProvidedCHO),
                     (DC.date,   Literal('2020')),
                     (DC.title,  Literal('The University of Chicago Library Digital Repository')),
                     (ERC.who,   Literal('University of Chicago Library')),
                     (ERC.what,  Literal('The University of Chicago Library Digital Repository')),
                     (ERC.when,  Literal('2020')),
                     (ERC.where, URIRef('https://repository.lib.uchicago.edu/digital_collections/mepa/')),
                     (EDM.year,  Literal('2020'))):
            self.graph.add((self.MEPA_CHO, p, o))

        # resource map
        self.rem_graph(self.MEPA_AGG, self.MEPA_REM, now)

    def triples(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base=BASE).decode("utf-8")


if __name__ == "__main__":
    options = docopt(__doc__)

    # get input data.
    tmp = ElementTree.parse('input/vcExport_v2.xml')
    vra = ElementTree.Element('{http://www.vraweb.org/vracore4.htm}vra')

    # get the work.
    for e in tmp.findall(
        './/vra:work[@refid="{}"]'.format(options['<work_refid>']),
        {'vra': 'http://www.vraweb.org/vracore4.htm'}
    ):
        vra.append(copy.deepcopy(e))

    # get recto and verso.
    for e in tmp.findall(
        './/vra:relation[@refid="{}"]/../..'.format(options['<work_refid>']),
        {'vra': 'http://www.vraweb.org/vracore4.htm'}
    ):
        vra.append(copy.deepcopy(e))

    edm = MepaToEDM(
        vra,
        'example'
    )
    edm.build_work_triples()
    edm.build_recto_verso_triples()
    sys.stdout.write(edm.triples())
