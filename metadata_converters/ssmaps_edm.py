#!/usr/bin/env python
"""Usage: ssmaps_edm [--debug] [--no_images] --digital_record_id <digital_record_id> --noid <noid>
"""

import datetime, io, json, hashlib, os, paramiko, re, requests, sys
import xml.etree.ElementTree as ElementTree
from classes import SocSciMapsMarcXmlToDc
from docopt import docopt
from io import BytesIO
from PIL import Image
from pymarc import MARCReader
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, DC, DCTERMS, XSD

Image.MAX_IMAGE_PIXELS = 1000000000


ARK     = Namespace('https://www.lib.uchicago.edu/ark:61001/')
BF      = Namespace('http://id.loc.gov/ontologies/bibframe/')
EBUCORE = Namespace('https://www.ebu.ch/metadata/ontologies/ebucore/')
EDM     = Namespace('http://www.europeana.eu/schemas/edm/')
ERC     = Namespace('http://purl.org/kernel/elements/1.1/')
MADSRDF = Namespace('http://www.loc.gov/mads/rdf/v1#')
MIX     = Namespace('http://www.loc.gov/mix/v20/')
OAI     = Namespace('http://www.openarchives.org/OAI/2.0/')
ORE     = Namespace('http://www.openarchives.org/ore/terms/')
PREMIS  = Namespace('info:lc/xmlns/premis-v2/')
PREMIS2 = Namespace('http://www.loc.gov/premis/rdf/v1#')
PREMIS3 = Namespace('http://www.loc.gov/premis/rdf/v3/')
VRA     = Namespace('http://purl.org/vra/')


def process_date_string(s):
    date_str = False
    # find every occurrence of either four digits in a row or three
    # digits followed by a dash.
    dates = re.findall('[0-9]{3}[0-9-]', s)
    # if there are two date chunks in the string, assume they are a date
    # range. (e.g. 'yyyy-yyyy'
    if len(dates) == 2:
        return '/'.join(dates)
    # if the date is three digits followed by a dash, assume it is a
    # date range for a decade. (e.g. 'yyy0-yyy9')
    elif len(dates) == 1 and dates[0][-1] == '-':
        return '{0}0/{0}9'.format(dates[0][:3])
    # otherwise assume that the four digit date is correct.
    elif len(dates) == 1:
        return dates[0]
    else:
        return ''


class SocSciMapsMarcXmlToEDM():

    graph = Graph()

    for prefix, ns in (('bf', BF), ('dc', DC), ('dcterms', DCTERMS),
                       ('ebucore', EBUCORE), ('edm', EDM), ('erc', ERC),
                       ('madsrdf', MADSRDF), ('mix', MIX), ('ore', ORE),
                       ('premis', PREMIS), ('premis2', PREMIS2),
                       ('premis3', PREMIS3)):
        graph.bind(prefix, ns)

    """A class to convert MARCXML to Europeana Data Model (EDM)."""
    def __init__(self, digital_record, print_record, noid, master_file_metadata):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        self.digital_record = digital_record
        self.print_record = print_record
        self.dc = SocSciMapsMarcXmlToDc(digital_record, print_record, noid)

        self.noid = noid
        self.ark = 'ark:61001/{}'.format(noid)
        self.master_file_metadata = master_file_metadata

        if isinstance(self.dc.identifier, list):
            self.identifier = self.dc.identifier[0]
        else:
            self.identifier = self.dc.identifier

        self.agg = ARK['{}/aggregation'.format(self.noid)]
        self.cho = ARK['{}'.format(self.noid)]
        self.pro = ARK['{}/file.dc.xml'.format(self.noid)]
        self.rem = ARK['{}/rem'.format(self.noid)]
        self.wbr = ARK['{}/file.tif'.format(self.noid)]

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
        self.graph.add((self.agg, RDF.type,          ORE.Aggregation))
        self.graph.add((self.agg, EDM.aggregatedCHO, self.cho))
        self.graph.add((self.agg, EDM.dataProvider,  Literal("University of Chicago Library")))
        self.graph.add((self.agg, EDM.hasView,       self.wbr))
        self.graph.add((self.agg, EDM.isShownBy,     URIRef('https://ark.lib.uchicago.edu/{}/file.tif'.format(self.ark))))
        self.graph.add((self.agg, EDM.object,        URIRef('https://ark.lib.uchicago.edu/{}/file.tif'.format(self.ark))))
        self.graph.add((self.agg, EDM.provider,      Literal('University of Chicago Library')))
        self.graph.add((self.agg, EDM.rights,        URIRef('https://rightsstatements.org/vocab/NoC−US/1.0/')))
        self.graph.add((self.agg, ORE.isDescribedBy, self.rem))

        self._build_cho()

        # proxy for the item.
        self.graph.add((self.pro, RDF.type,          ORE.Proxy))
        self.graph.add((self.pro, URIRef('http://purl.org/dc/elements/1.1/format'), 
                                                     Literal('application/xml')))
        self.graph.add((self.pro, ORE.proxyFor,      self.cho))
        self.graph.add((self.pro, ORE.proxyIn,       self.agg))

        # resource map for the item.
        self.graph.add((self.rem, DCTERMS.created,   self.now))
        self.graph.add((self.rem, DCTERMS.modified,  self.now))
        self.graph.add((self.rem, DCTERMS.creator,   URIRef('https://www.lib.uchicago.edu/')))
        self.graph.add((self.rem, RDF.type,          ORE.ResourceMap))
        self.graph.add((self.rem, ORE.describes,     self.agg))

        self._build_web_resources()

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
            (BF.ClassificationLcc,    '{http://id.loc.gov/ontologies/bibframe/}ClassificationLcc'),
            (BF.place,                '{http://id.loc.gov/ontologies/bibframe/}place'),
            (BF.scale,                '{http://id.loc.gov/ontologies/bibframe/}scale'),
            (DC.creator,              '{http://purl.org/dc/elements/1.1/}creator'),
            (DC.description,          '{http://purl.org/dc/elements/1.1/}description'),
            (DC.language,             '{http://purl.org/dc/elements/1.1/}language'),
            (DC.publisher,            '{http://purl.org/dc/elements/1.1/}publisher'),
            (DC.rights,               '{http://purl.org/dc/elements/1.1/}rights'),
            (DC.subject,              '{http://purl.org/dc/elements/1.1/}subject'),
            (DC.title,                '{http://purl.org/dc/elements/1.1/}title'),
            (DC.type,                 '{http://purl.org/dc/elements/1.1/}type'),
            (DCTERMS.dateCopyrighted, '{http://purl.org/dc/terms/}dateCopyrighted'),
            (DCTERMS.extent,          '{http://purl.org/dc/terms/}extent'),
            (DCTERMS.hasFormat,       '{http://purl.org/dc/terms/}hasFormat'),
            (DCTERMS.spatial,         '{http://purl.org/dc/terms/}spatial'),
            (ERC.what,                '{http://purl.org/dc/elements/1.1/}title'),
            (ERC.who,                 '{http://www.loc.gov/mads/rdf/v1#}ConferenceName'),
            (ERC.who,                 '{http://www.loc.gov/mads/rdf/v1#}CorporateName'),
            (ERC.who,                 '{http://www.loc.gov/mads/rdf/v1#}PersonalName'),
            (MADSRDF.ConferenceName,  '{http://www.loc.gov/mads/rdf/v1#}ConferenceName'),
            (MADSRDF.CorporateName,   '{http://www.loc.gov/mads/rdf/v1#}CorporateName'),
            (MADSRDF.PersonalName,    '{http://www.loc.gov/mads/rdf/v1#}PersonalName')
        ):
            for dc_obj_el in self.dc._asxml().findall(obj_str):
                self.graph.add((self.cho, pre, Literal(dc_obj_el.text)))

        self.graph.add((self.cho, DCTERMS.identifier, URIRef('https://n2t.net/{}'.format(self.ark))))
        self.graph.add((self.cho, DCTERMS.rights,     URIRef('https://rightsstatements.org/vocab/NoC-US/1.0/')))
        self.graph.add((self.cho, ERC.where,          URIRef('https://ark.lib.uchicago.edu/{}'.format(self.ark))))

        for dc_obj_el in self.dc._asxml().findall('{http://id.loc.gov/ontologies/bibframe/}Local'):
            self.graph.add((self.cho, BF.Local, URIRef(dc_obj_el.text)))

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

        self.graph.add((self.cho, EDM.currentLocation, Literal('Map Collection Reading Room (Room 370)')))

        self.graph.add((self.cho, EDM.type, Literal('IMAGE')))

    def _build_web_resources(self):
        assert(len(self.master_file_metadata) == 1)

        metadata = self.master_file_metadata[0]
        self.graph.add((self.wbr, RDF.type,                  EDM.WebResource))
        self.graph.add((self.wbr, EBUCORE.hasMimeType,       Literal('image/tiff')))

        fixity = BNode()
        self.graph.add((self.wbr, PREMIS3.fixity,            fixity))
        self.graph.add((fixity,   RDF.type,                  URIRef('https://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/sha512')))
        self.graph.add((fixity,   RDF.value,                 Literal('TODO')))
        self.graph.add((self.wbr,  PREMIS3.compositionLevel, Literal(0)))
        self.graph.add((self.wbr, PREMIS3.originalName,      Literal(metadata['name'])))
        self.graph.add((self.wbr, PREMIS3.size,              Literal(metadata['size'])))

    @classmethod
    def triples(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base='https://www.lib.uchicago.edu/ark:61001/')


def marc_to_edm_soc_sci(no_images, digital_record_id, noid, debug=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ['SOLR_ACCESS_DOMAIN'],
        username=os.environ['SOLR_ACCESS_USERNAME'],
        password=os.environ['SOLR_ACCESS_PASSWORD']
    )

    if debug:
        sys.stderr.write('marc_edm requesting digital record.\n')

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

    if debug:
        sys.stderr.write('marc_edm requesting print record.\n')

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
            if debug:
                sys.stderr.write('marc_edm requesting tiff.\n')
            mime_type = 'image/tiff'
            response = requests.get(
                'https://ocfl.lib.uchicago.edu/ark:61001/{}/file.tif'.format(noid)
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
            options['<noid>'],
            options['--debug']
        )
    )
