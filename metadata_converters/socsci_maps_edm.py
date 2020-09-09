#!/usr/bin/env python
"""Usage: socsci_maps_edm.py [--no_images] --digital_record_id <digital_record_id> --noid <noid>
"""

import datetime, io, json, hashlib, os, paramiko, requests, sys
import xml.etree.ElementTree as ElementTree
from classes import BASE, BF, EDM, ERC, MADSRDF, MIX, OAI, ORE, PREMIS, PREMIS2, PREMIS3, VRA
from classes import DigitalCollectionToEDM, process_date_string, SocSciMapsMarcXmlToDc
from docopt import docopt
from io import BytesIO
from PIL import Image
from pymarc import MARCReader
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, DC, DCTERMS, XSD

Image.MAX_IMAGE_PIXELS = 1000000000


class SocSciMapsMarcXmlToEDM(DigitalCollectionToEDM):
    """A class to convert MARCXML to Europeana Data Model (EDM)."""

    # from Charles, via Slack (10/3/2019 9:52am)
    # For the TIFF image we also need a edm:WebResource. Ideally we would want
    # the original form of the metadata (whether .xml or .mrc), a ore:Proxy.

    MAPCOL_AGG = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/aggregation')
    MAPCOL_CHO = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/')
    MAPCOL_REM = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/rem')

    SSMAPS_AGG = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc/aggregation')
    SSMAPS_CHO = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc/')
    SSMAPS_REM = URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc/rem')

    graph = Graph()
    for prefix, ns in (('bf', BF), ('dc', DC), ('dcterms', DCTERMS),
                       ('edm', EDM), ('erc', ERC), ('madsrdf', MADSRDF),
                       ('mix', MIX), ('ore', ORE), ('premis', PREMIS),
                       ('premis2', PREMIS2), ('premis3', PREMIS3)):
        graph.bind(prefix, ns)

    def __init__(self, digital_record, print_record, noid, master_file_metadata):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        self.digital_record = digital_record
        self.print_record = print_record
        self.dc = SocSciMapsMarcXmlToDc(digital_record, print_record, noid)
        self.noid = noid
        self.master_file_metadata = master_file_metadata

        if isinstance(self.dc.identifier, list):
            self.identifier = self.dc.identifier[0]
        else:
            self.identifier = self.dc.identifier

        self.short_id = self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')

        self.agg = URIRef('ark:/61001/{}/aggregation'.format(self.noid))
        self.cho = URIRef('ark:/61001/{}'.format(self.noid))
        self.pro = URIRef('ark:/61001/{}/file.xml'.format(self.noid))
        self.rem = URIRef('ark:/61001/{}/rem'.format(self.noid))
        self.wbr = URIRef('ark:/61001/{}/file.tif'.format(self.noid))

        self.now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

    def build_item_triples(self):
        """Add triples for an individual item.

        Aggregations exist because things on the web like web sites or
        collections of web pages actually include several resources, even
        though we refer to them by a single resource, like a home page.
        See the ORE Primer (http://www.openarchives.org/ore/1.0/primer)
        for more information. This is a bit abstract in the case of the social
        scientist maps, where the model currently includes a single web page 
        per map. 

        The Cultural Heritage Object is the map itself.

        Side Effect:
            Add triples to self.graph
        """
        # aggregation for the item.
        self.graph.add((self.agg, RDF.type,           ORE.Aggregation))
        self.graph.add((self.agg, EDM.aggregatedCHO,  self.cho))
        self.graph.add((self.agg, EDM.dataProvider,   Literal("University of Chicago Library")))
        self.graph.add((self.agg, ORE.isDescribedBy,  self.rem))
        self.graph.add((self.agg, EDM.isShownBy,      self.wbr))
        self.graph.add((self.agg, EDM.object,         self.wbr))
        self.graph.add((self.agg, EDM.provider,       Literal('University of Chicago Library')))
        self.graph.add((self.agg, EDM.rights,         URIRef('http://creativecommons.org/licenses/by−sa/4.0/')))

        self._build_cho()

        # proxy for the item.
        self.graph.add((self.pro,      RDF.type,      ORE.Proxy))
        self.graph.add((self.pro,      URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.pro,      ORE.proxyFor,  self.cho))
        self.graph.add((self.pro,      ORE.proxyIn,   self.agg))

        # resource map for the item.
        self.graph.add((self.rem,      DCTERMS.created,    self.now))
        self.graph.add((self.rem,      DCTERMS.modified,   self.now))
        self.graph.add((self.rem,      DCTERMS.creator,    URIRef('https://library.uchicago.edu')))
        self.graph.add((self.rem,      RDF.type,           ORE.ResourceMap))
        self.graph.add((self.rem,      ORE.describes,      self.agg))

        self._build_web_resources()

        # connect the item to its collection.
        self.graph.add((self.SSMAPS_CHO, DCTERMS.hasPart, self.cho))

    def _build_cho(self):
        """The cultural herigate object is the map itself. 

        This method adds triples that describe the cultural heritage object.

        Args:
            agg (URIRef): aggregation 
            cho (URIRef): cultural heritage object

        Side Effect:
            Add triples to self.graph
        """

        self.graph.add((self.cho, RDF.type, EDM.ProvidedCHO))
        for pre, obj_str in (
            (BF.ClassificationLcc,   '{http://id.loc.gov/ontologies/bibframe/}ClassificationLcc'),
            (MADSRDF.ConferenceName, '{http://www.loc.gov/mads/rdf/v1#}ConferenceName'),
            (MADSRDF.CorporateName,  '{http://www.loc.gov/mads/rdf/v1#}CorporateName'),
            (DC.coverage,            '{http://purl.org/dc/elements/1.1/}coverage'),
            (DC.creator,             '{http://purl.org/dc/elements/1.1/}creator'),
            (DC.description,         '{http://purl.org/dc/elements/1.1/}description'),
            (DC.extent,              '{http://purl.org/dc/elements/1.1/}extent'),
            (DCTERMS.hasFormat,      '{http://purl.org/dc/terms/}hasFormat'),
            (DC.identifier,          '{http://purl.org/dc/elements/1.1/}identifier'),
            (DC.language,            '{http://purl.org/dc/elements/1.1/}language'),
            (BF.Local,               '{http://id.loc.gov/ontologies/bibframe/}Local'),
            (MADSRDF.PersonalName,   '{http://www.loc.gov/mads/rdf/v1#}PersonalName'),
            (BF.place,               '{http://id.loc.gov/ontologies/bibframe/}place'),
            (DC.publisher,           '{http://purl.org/dc/elements/1.1/}publisher'),
            (DC.rights,              '{http://purl.org/dc/elements/1.1/}rights'),
            (BF.scale,               '{http://id.loc.gov/ontologies/bibframe/}scale'),
            (DCTERMS.spatial,        '{http://purl.org/dc/terms/}spatial'),
            (DC.subject,             '{http://purl.org/dc/elements/1.1/}subject'),
            (DC.title,               '{http://purl.org/dc/elements/1.1/}title'),
            (DC.type,                '{http://purl.org/dc/elements/1.1/}type'),
            (ERC.what,               '{http://purl.org/dc/elements/1.1/}title'),
            (ERC.who,                '{http://www.loc.gov/mads/rdf/v1#}ConferenceName'),
            (ERC.who,                '{http://www.loc.gov/mads/rdf/v1#}CorporateName'),
            (ERC.who,                '{http://www.loc.gov/mads/rdf/v1#}PersonalName')
        ):
            for dc_obj_el in self.dc._asxml().findall(obj_str):
                self.graph.add((self.cho, pre, Literal(dc_obj_el.text)))

        # dc:date
        d = []

        for f in self.digital_record.get_fields('260', '264'):
            for sf in f.get_subfields('c'):
                d.append(sf)
        if d:
            self.graph.add((self.cho, DC.date, Literal(process_date_string(d[0]))))
            self.graph.add((self.cho, EDM.year, Literal(process_date_string(d[0]))))
            self.graph.add((self.cho, ERC.when, Literal(process_date_string(d[0]))))

        # dc:format
        for dc_obj_el in self.dc._asxml().findall('{http://purl.org/dc/elements/1.1/}format'):
            self.graph.add((
                self.cho, 
                URIRef('http://purl.org/dc/elements/1.1/format'),
                Literal(dc_obj_el.text)
            ))

        # dc:rights
        self.graph.add((
            self.cho, 
            URIRef('http://purl.org/dc/elements/1.1/rights'),
            URIRef('http://creativecommons.org/licenses/by-sa/4.0/')
        ))

        self.graph.add((self.cho, DCTERMS.isPartOf, URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc')))
        self.graph.add((self.cho, EDM.currentLocation, Literal('Map Collection Reading Room (Room 370)')))
        self.graph.add((self.cho, EDM.type, Literal('IMAGE')))
        self.graph.add((self.cho, ERC.where, self.cho))

    def _build_web_resources(self):
        for metadata in self.master_file_metadata:
            self.graph.add((self.wbr, RDF.type, EDM.WebResource))
            for p, o in (
                ('http://www.loc.gov/premis/rdf/v1#hasIdentifierType',         'ark:/61001'),
                ('http://www.loc.gov/premis/rdf/v1#hasIdentifierValue',        '{}/file.tif'.format(self.noid)),
                ('http://www.loc.gov/premis/rdf/v3/compositionLevel',          0),
                ('http://www.loc.gov/premis/rdf/v1#hasMessageDigestAlgorithm', 'SHA-512'),
                ('http://www.loc.gov/premis/rdf/v1#hasMessageDigest',          metadata['sha512']),
                ('http://www.loc.gov/premis/rdf/v3/size',                      metadata['size']),
                ('http://www.loc.gov/premis/rdf/v1#hasFormatName',             'image/tiff'),
                ('http://www.loc.gov/premis/rdf/v3/originalName',              metadata['name']),
                ('http://www.loc.gov/premis/rdf/v3/restriction',               'None'),
                ('http://purl.org/dc/elements/1.1/format',                     'image/tiff')):
                self.graph.add((self.wbr, URIRef(p), Literal(o)))

    @classmethod
    def build_repository_triples(self):
        """Add triples for the repository itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # resource map for the repository
        self.graph.add((self.REPOSITORY_REM, RDF.type,          ORE.ResourceMap))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.created,   now))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.modified,  now))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.creator,   URIRef('https://library.uchicago.edu/')))
        self.graph.add((self.REPOSITORY_REM, ORE.describes,     self.REPOSITORY_AGG))

        # aggregation for the repository
        self.graph.add((self.REPOSITORY_AGG, RDF.type,          ORE.Aggregation))
        self.graph.add((self.REPOSITORY_AGG, EDM.aggregatedCHO, self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_AGG, EDM.dataProvider,  Literal("University of Chicago Library")))
        self.graph.add((self.REPOSITORY_AGG, EDM.isShownAt,     self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_AGG, EDM.object,        URIRef('https://repository.lib.uchicago.edu/icon.png')))
        self.graph.add((self.REPOSITORY_AGG, EDM.provider,      Literal('University of Chicago Library')))
        self.graph.add((self.REPOSITORY_AGG, ORE.isDescribedBy, self.REPOSITORY_REM))

        # cultural heritage object for the repository
        self.graph.add((self.REPOSITORY_CHO, RDF.type,          EDM.ProvidedCHO))
        self.graph.add((self.REPOSITORY_CHO, DC.date,           Literal('2020')))
        self.graph.add((self.REPOSITORY_CHO, DC.title,          Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.REPOSITORY_CHO, DCTERMS.hasPart,   URIRef('https://repository.lib.uchicago.edu/digital_archives')))
        self.graph.add((self.REPOSITORY_CHO, DCTERMS.hasPart,   URIRef('https://repository.lib.uchicago.edu/digital_collections')))
        self.graph.add((self.REPOSITORY_CHO, ERC.who,           Literal('University of Chicago Library')))
        self.graph.add((self.REPOSITORY_CHO, ERC.what,          Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.REPOSITORY_CHO, ERC.when,          Literal('2020')))
        self.graph.add((self.REPOSITORY_CHO, ERC.where,         self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_CHO, EDM.year,          Literal('2020'))) 

    @classmethod
    def build_digital_collections_triples(self):
        """Add triples for digital collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # resource map for digital collections.
        self.graph.add((self.DIGCOL_REM, RDF.type,           ORE.ResourceMap))
        self.graph.add((self.DIGCOL_REM, DCTERMS.created,    now))
        self.graph.add((self.DIGCOL_REM, DCTERMS.modified,   now))
        self.graph.add((self.DIGCOL_REM, DCTERMS.creator,    URIRef('https://library.uchicago.edu/')))
        self.graph.add((self.DIGCOL_REM, ORE.describes,      self.DIGCOL_AGG))

        # aggregation for digital collections
        self.graph.add((self.DIGCOL_AGG, RDF.type,           ORE.Aggregation))
        self.graph.add((self.DIGCOL_AGG, EDM.aggregatedCHO,  self.DIGCOL_CHO))
        self.graph.add((self.DIGCOL_AGG, EDM.dataProvider,   Literal('University of Chicago Library')))
        self.graph.add((self.DIGCOL_AGG, EDM.isShownAt,      URIRef('https://repository.lib.uchicago.edu/digital_collections/')))
        self.graph.add((self.DIGCOL_AGG, EDM.object,         URIRef('https://repository.lib.uchicago.edu/digital_collections/icon.png')))
        self.graph.add((self.DIGCOL_AGG, EDM.provider,       Literal('University of Chicago Library')))
        self.graph.add((self.DIGCOL_AGG, ORE.isDescribedBy,  self.DIGCOL_REM))

        # cultural heritage object for digital collections
        self.graph.add((self.DIGCOL_CHO, RDF.type,           EDM.ProvidedCHO))
        self.graph.add((self.DIGCOL_CHO, DC.date,            Literal('2020')))
        self.graph.add((self.DIGCOL_CHO, DC.title,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.DIGCOL_CHO, DCTERMS.hasPart,    URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/')))
        self.graph.add((self.DIGCOL_CHO, ERC.who,            Literal('University of Chicago Library')))
        self.graph.add((self.DIGCOL_CHO, ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.DIGCOL_CHO, ERC.when,           Literal('2020')))
        self.graph.add((self.DIGCOL_CHO, ERC.where,          URIRef('https://repository.lib.uchicago.edu/digital_collections/')))
        self.graph.add((self.DIGCOL_CHO, EDM.year,           Literal('2020')))

    @classmethod
    def build_map_collection_triples(self):
        """Add triples for the map collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # resource map for the map collection 
        self.graph.add((self.MAPCOL_REM, RDF.type,           ORE.ResourceMap))
        self.graph.add((self.MAPCOL_REM, DCTERMS.created,    now))
        self.graph.add((self.MAPCOL_REM, DCTERMS.creator,    URIRef('https://library.uchicago.edu/')))
        self.graph.add((self.MAPCOL_REM, DCTERMS.modified,   now))
        self.graph.add((self.MAPCOL_REM, ORE.describes,      self.MAPCOL_AGG))

        # aggregation for the map collection
        self.graph.add((self.MAPCOL_AGG, RDF.type,           ORE.Aggregation))
        self.graph.add((self.MAPCOL_AGG, EDM.aggregatedCHO,  self.MAPCOL_CHO))
        self.graph.add((self.MAPCOL_AGG, EDM.dataProvider,   Literal('University of Chicago Library')))
        self.graph.add((self.MAPCOL_AGG, EDM.isShownAt,      self.MAPCOL_CHO))
        self.graph.add((self.MAPCOL_AGG, EDM.object,         URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/icon.png')))
        self.graph.add((self.MAPCOL_AGG, EDM.provider,       Literal('University of Chicago Library')))
        self.graph.add((self.MAPCOL_AGG, ORE.isDescribedBy,  self.MAPCOL_REM))

        # cultural heritage object for the map collection
        self.graph.add((self.MAPCOL_CHO, RDF.type,           EDM.ProvidedCHO))
        self.graph.add((self.MAPCOL_CHO, DC.date,            Literal('2020')))
        self.graph.add((self.MAPCOL_CHO, DC.title,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.MAPCOL_CHO, DCTERMS.hasPart,    self.SSMAPS_CHO))
        self.graph.add((self.MAPCOL_CHO, ERC.who,            Literal('University of Chicago Library')))
        self.graph.add((self.MAPCOL_CHO, ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.MAPCOL_CHO, ERC.when,           Literal('2020')))
        self.graph.add((self.MAPCOL_CHO, ERC.where,          URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/')))
        self.graph.add((self.MAPCOL_CHO, EDM.year,           Literal('2020')))

    @classmethod
    def build_socscimap_collection_triples(self):
        """Add triples for the social scientist map collection, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # resource map for the social scientists map collection
        self.graph.add((self.SSMAPS_REM, RDF.type,           ORE.ResourceMap))
        self.graph.add((self.SSMAPS_REM, DCTERMS.created,    now))
        self.graph.add((self.SSMAPS_REM, DCTERMS.creator,    URIRef('https://library.uchicago.edu/')))
        self.graph.add((self.SSMAPS_REM, ORE.describes,      self.SSMAPS_AGG))

        # aggregation for the social scientist maps collection
        self.graph.add((self.SSMAPS_AGG, RDF.type,           ORE.Aggregation))
        self.graph.add((self.SSMAPS_AGG, EDM.aggregatedCHO,  self.SSMAPS_CHO))
        self.graph.add((self.SSMAPS_AGG, EDM.dataProvider,   Literal('University of Chicago Library')))
        self.graph.add((self.SSMAPS_AGG, EDM.isShownAt,      self.SSMAPS_CHO))
        self.graph.add((self.SSMAPS_AGG, EDM.object,         URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc/icon.png')))
        self.graph.add((self.SSMAPS_AGG, EDM.provider,       Literal('University of Chicago Library')))
        self.graph.add((self.SSMAPS_AGG, ORE.isDescribedBy,  self.SSMAPS_REM))

        # cultural heritage object for the social scientist maps collection
        self.graph.add((self.SSMAPS_CHO, RDF.type,           EDM.ProvidedCHO))
        self.graph.add((self.SSMAPS_CHO, DC.date,            Literal('2020')))
        self.graph.add((self.SSMAPS_CHO, DC.title,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.SSMAPS_CHO, ERC.who,            Literal('University of Chicago Library')))
        self.graph.add((self.SSMAPS_CHO, ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.SSMAPS_CHO, ERC.when,           Literal('2020')))
        self.graph.add((self.SSMAPS_CHO, ERC.where,          URIRef('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc/')))
        self.graph.add((self.SSMAPS_CHO, EDM.year,           Literal('2020')))

    @classmethod
    def triples(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base=BASE).decode("utf-8")

def marc_to_edm_soc_sci(no_images, digital_record_id, noid):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ['SOLR_ACCESS_DOMAIN'],
        username=os.environ['SOLR_ACCESS_USERNAME'],
        password=os.environ['SOLR_ACCESS_PASSWORD']
    )

    # request the digital record
    url = 'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=id:{}'.format(str(digital_record_id))
    _, ssh_stdout, _ = ssh.exec_command('curl "{}"'.format(url))
    data = json.loads(ssh_stdout.read())
    fullrecord = data['response']['docs'][0]['fullrecord']

    with io.BytesIO(fullrecord.encode('utf-8')) as fh:
        reader = MARCReader(fh)
        for record in reader:
            digital_record = record

    # get an oclc number for the print record
    oclc_num = digital_record['776']['w'].replace('(OCoLC)', '')

    # request the print record
    url = 'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=oclc_num:{}'.format(str(oclc_num))
    _, ssh_stdout, _ = ssh.exec_command('curl "{}"'.format(url))
    data = json.loads(ssh_stdout.read())
    fullrecord = data['response']['docs'][0]['fullrecord']

    with io.BytesIO(fullrecord.encode('utf-8')) as fh:
        reader = MARCReader(fh)
        for record in reader:
            print_record = record

    identifier = digital_record['856']['u'].split('/').pop()

    if no_images:
        image_data = []
    else:
        try:
            mime_type = 'image/tiff'
            response = requests.get(
                'http://ark.lib.uchicago.edu/ark:/61001/{}/file.tif'.format(noid)
            )
            size = len(response.content)
            img = Image.open(BytesIO(response.content))
            width = img.size[0]
            height = img.size[1]
            md5 = hashlib.md5(response.content).hexdigest()
            sha512 = hashlib.sha512(response.content).hexdigest()
        except AttributeError:
            sys.stdout.write('trouble with tiff file.\n')
            sys.exit()

        image_data = [{
            'height': height,
            'md5': md5,
            'mime_type': mime_type,
            'name': '{}.tif'.format(identifier),
            'sha512': sha512,
            'size': size,
            'width': width
        }]

    edm = SocSciMapsMarcXmlToEDM(
        digital_record,
        print_record,
        noid,
        image_data
    )
    edm.build_item_triples()
    return SocSciMapsMarcXmlToEDM.triples()

if __name__ == "__main__":
    options = docopt(__doc__)
    sys.stdout.write(
        marc_to_edm_soc_sci(
            options['--no_images'],
            options['<digital_record_id>'], 
            options['<noid>']
        )
    )
