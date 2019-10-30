import datetime
import getpass
import hashlib
import jinja2
import json
import magic
import os
import paramiko
import re
import sys
import xml.etree.ElementTree as ElementTree

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, DC, DCTERMS, XSD
from rdflib.plugins.sparql import prepareQuery

class MarcXmlConverter:
    """
    A class to convert MARCXML to other formats. Extend this class to make
    converters for outputting specific formats. 

    Returns:
        a MarcXmlConverter
    """

    def __init__(self, marcxml):
        """Initialize an instance of the class MarcXmlConverter.

        Args:
            marcxml (str): a marcxml collection with a single record.
        """
        self.record = ElementTree.fromstring(marcxml).find(
            '{http://www.loc.gov/MARC21/slim}record')

        # Only bring in 655's where the $2 subfield is set to 'lcgft'.
        remove = []
        for element in self.record:
            if element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                if element.attrib['tag'] == '655':
                    for subfield in element:
                        if subfield.attrib['code'] == '2' and not subfield.text == 'lcgft':
                            remove.append(element)
                            break
        for element in remove:
            self.record.remove(element)

    def get_marc_field(self, field_tag, subfield_code, ind1, ind2):
        """Get a specific MARC field. 

        Args:
            field_tag (str): e.g., "245"
            subfield_code (str): subfield codes as a regex, e.g. '[a-z]'
            ind1 (str): first indicator as a regex, e.g. '4'
            ind2 (str): second indicator as a regex, e.g. '4'

        Returns:
            list: of strings, all matching MARC tags and subfields.
        """
        results = []
        for element in self.record:
            try:
                if not element.attrib['tag'] == field_tag:
                    continue
            except KeyError:
                continue
            if element.tag == '{http://www.loc.gov/MARC21/slim}controlfield':
                results.append(element.text)
            elif element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                if not re.match(ind1, element.attrib['ind1']):
                    continue
                if not re.match(ind2, element.attrib['ind2']):
                    continue
                for subfield in element:
                    if re.match(subfield_code, subfield.attrib['code']):
                        results.append(subfield.text)
        return results


class SocSciMapsMarcXmlToDc:
    """ If any exclude condition is met, the item will be excluded. If any filter
        condition is met, the item will be filtered. """
    def __init__(self, marcxml):
        ElementTree.register_namespace(
            'dc', 'http://purl.org/dc/elements/1.1/')
        ElementTree.register_namespace(
            'dcterms', 'http://purl.org/dc/terms/')
        self.record = ElementTree.fromstring(marcxml).find(
            '{http://www.loc.gov/MARC21/slim}record')
        with open(os.path.join(os.path.dirname(__file__), 'json/socscimaps_marc2dc.json')) as f:
            data = json.load(f)
            self.template = data['template']
            self.crosswalk = data['crosswalk']

    def _filter_datafield(self, datafield, f):
        """Return true if any subfields exist that match the conditions in r. 

        Args:
            datafield (xml.etree.ElementTree.Element): a MARCXML datafield element.
            f (dict): a rule, e.g.: { "subfield_re": "2", "value_re": "^fast$" }

        Returns:
            bool: datafield matches. 
        """
        for subfield in datafield.findall('{http://www.loc.gov/MARC21/slim}subfield'):
            if bool(re.search(f['subfield_re'], subfield.get('code'))) and \
               bool(re.search(f['value_re'], subfield.text)):
                return True
        return False

    def _get_subfield_values(self, datafield, r):
        """
        Return true if any subfields exist that match the conditions in r. 

        Args:
            datafield (xml.etree.ElementTree.Element): a MARCXML datafield element.
            r (dict): a rule, e.g.: { "tag_re": "700", "subfield_re": "a" }

        Returns:
            A list of strings. 
        """
        values = []
        for subfield in datafield.findall('{http://www.loc.gov/MARC21/slim}subfield'):
            if re.search(r['subfield_re'], subfield.get('code')):
                values.append(subfield.text)
        return values

    def _get_datafield_values(self, record, r):
        """Return a list of values for a datafield. Only process datafields
        with the appropriate tag and indicator values.

        Args:
            record (xml.etree.ElementTree.Element): a MARCXML record element.
            r (dict): a rule, e.g. { "tag_re": "700", "subfield_re": "a" }

        Returns:
            A list of strings.
        """
        values = []
        for datafield in record.findall('{http://www.loc.gov/MARC21/slim}datafield'):
            if re.search(r['tag_re'], datafield.get('tag')) == None:
                continue
            if re.search(r['indicator1_re'], datafield.get('ind1')) == None:
                continue
            if re.search(r['indicator2_re'], datafield.get('ind2')) == None:
                continue

            _exclude = False
            for f in r['exclude']:
                if self._filter_datafield(datafield, f):
                    _exclude = True
            if _exclude:
                continue
  
            _filter = True
            if r['filter']:
                _filter = False
                for f in r['filter']:
                    if self._filter_datafield(datafield, f):
                        _filter = True
            if not _filter:
                continue

            if r['join_subfields']:
                values.append(' '.join(self._get_subfield_values(datafield, r)))
            else:
                values.extend(self._get_subfield_values(datafield, r))
        if r['return_first_result_only'] and values:
            return [values[0]]
        elif r['join_fields']:
            return [' '.join(values)]
        else:
            return values

    def __getattr__(self, attr):
        """Return individual Dublin Core elements as instance properties, e.g.
        self.identifier.
        Returns:
            list
        """
        values = []
        for e in self._asxml().findall(
	    '{{http://purl.org/dc/elements/1.1/}}{}'.format(attr.replace('_','.'))
        ):
            values.append(e.text)
        for e in self._asxml().findall(
	    '{{http://purl.org/dc/terms/}}{}'.format(attr.replace('_','.'))
        ):
            values.append(e.text)
        return sorted(values)

    def _asxml(self):
        metadata = ElementTree.Element('metadata')
        for e, rules in self.crosswalk.items():
            values = []
            for r in rules:
                values.extend(
                    self._get_datafield_values(
                        self.record,
                        {**self.template, **r}
                    )
                )
            element_str = e.replace('dc:', '{http://purl.org/dc/elements/1.1/}').replace('dcterms:', '{http://purl.org/dc/terms/}')
            for value in values:
                ElementTree.SubElement(
                    metadata,
                    element_str
                ).text = value
        return metadata
            
    def __str__(self):
        return ElementTree.tostring(self._asxml(), 'utf-8', method='xml').decode('utf-8')


class MarcXmlToSchemaDotOrg(MarcXmlConverter):
    """A class to convert MARCXML to Schema.org."""

    mappings = [
        ('about',               [False, [('050', '[a-z]', '.', '.'),
                                         ('650', 'x',     '.', '.')], False, '[. ]*$']),
        ('alternativeName',     [False, [('246', '[a-z]', '.', '.')], False, None]),
        ('contentLocation',     [False, [('043', '[a-z]', '.', '.'),
                                         ('052', '[a-z]', '.', '.'),
                                         ('651', 'a',     '.', '.')], False, None]),
        ('contributor',         [True,  [('700', 'a',     '.', '.'),
                                         ('710', 'a',     '.', '.')], False, None]),
        ('copyrightYear',       [True,  [('264', 'c',     '4', '.')], False, None]),
        ('dateCreated',         [True,  [('533', 'd',     '.', '.')], False, None]),
        ('datePublished',       [True,  [('264', 'c',     '1', '.')], False, None]),
        ('description',         [False, [('500', '[a-z]', '.', '.'),
                                         ('538', '[a-z]', '.', '.')], False, None]),
        ('encoding',            [True,  [('533', 'a',     '.', '.')], False, None]),
        ('height',              [True,  [('300', 'c',     '.', '.')], False, None]),
        ('genre',               [True,  [('650', 'v',     '.', '.'),
                                         ('651', 'v',     '.', '.')], False, '^Maps[. ]*$|[. ]*$']),
        ('identifier',          [True,  [('020', '[a-z]', '.', '.'),
                                         ('021', '[a-z]', '.', '.'),
                                         ('022', '[a-z]', '.', '.'),
                                         ('023', '[a-z]', '.', '.'),
                                         ('024', '[a-z]', '.', '.'),
                                         ('025', '[a-z]', '.', '.'),
                                         ('026', '[a-z]', '.', '.'),
                                         ('027', '[a-z]', '.', '.'),
                                         ('028', '[a-z]', '.', '.'),
                                         ('029', '[a-z]', '.', '.')], False, None]),
        ('inLanguage',          [True,  [('041', '[a-z]', '.', '.')], False, None]),
        ('isAccessibleForFree', [False, [('506', '[a-z]', '.', '.')], False, None]),
        ('isPartOf',            [True,  [('490', '[a-z]', '.', '.'),
                                         ('533', 'f',     '.', '.'),
                                         ('700', '[at]',  '.', '.'),
                                         ('830', '[a-z]', '.', '.')], False, None]),
        ('locationCreated',     [True,  [('264', 'a',     '1', '.'),
                                         ('533', 'b',     '.', '.')], False, None]),
        ('mapType',             [True,  [('655', 'a',     '.', '.')], True,  '[. ]*$']),
        ('name',                [True,  [('130', '[a-z]', '.', '.'),
                                         ('240', '[a-z]', '.', '.'),
                                         ('245', '[ab]',  '.', '.')], False, None]),
        ('publisher',           [True,  [('264', 'b',     '1', '.')], False, None]),
        ('spatialCoverage',     [False, [('255', '[a-z]', '.', '.')], False, None]),
        ('temporalCoverage',    [True,  [('650', 'y',     '.', '.')], False, None]),
        ('url',                 [True,  [('856', 'u',     '.', '.')], False, None]),
        ('width',               [True,  [('300', 'c',     '.', '.')], False, None])
    ]

    def __init__(self, marcxml):
        """Initialize an instance of the class MarcToSchemaDotOrg.

        Args:
            marcxml (str): a marcxml collection with a single record. 
        """
        for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
            if repeat_dc == False:
                assert repeat_sf == False
        super().__init__(marcxml)

    def _get_creator(self):
        """Get creators from the 100, 110, or 111 fields if possible. 
        Otherwise get them from the 245c.

        Returns:
            dict
        """
        if self.get_marc_field('100', '[a-z]', '.', '.'):
            creator_type = 'Person'
        else:
            creator_type = 'Organization'

        creators = []
        for m in ('100', '110', '111'):
            creator_str = ' '.join(self.get_marc_field(m, '[a-z]', '.', '.'))
            if creator_str:
                creators.append(creator_str)
        if not creators:
            creators = [' '.join(self.get_marc_field('245', 'c', '.', '.'))]

        if len(creators) == 0:
            return None
        elif len(creators) == 1:
            return {'@type': creator_type, 'name': creators[0]}
        else:
            return [{'@type': creator_type, 'name': c} for c in creators]

    def __call__(self):
        """Return Schema.org data as a dictionary.

        Returns:
            dict
        """
        dict_ = {
            '@context':    'https://schema.org',
            '@type':       'Map',
            'creator':     self._get_creator()
        }
        for k in dict_.keys():
            if dict_[k] == None:
                dict_.pop(k)

        for schema_element, (repeat_schema, marc_fields, repeat_sf, strip_out) in self.mappings:
            if repeat_schema:
                field_texts = set() 
                if repeat_sf:
                    for marc_field in marc_fields:
                        for field_text in self.get_marc_field(*marc_field):
                            if strip_out:
                                field_text = re.sub(strip_out, '', field_text)
                            if field_text:
                                field_texts.add(field_text)
                    if len(field_texts) == 1:
                        dict_[schema_element] = list(field_texts)[0]
                    elif len(field_texts) > 1:
                        dict_[schema_element] = sorted(field_texts)
                else:
                    for marc_field in marc_fields:
                        field_text = ' '.join(self.get_marc_field(*marc_field))
                        if strip_out:
                            field_text = re.sub(strip_out, '', field_text)
                        if field_text:
                            field_texts.add(field_text)
                    if len(field_texts) == 1:
                        dict_[schema_element] = list(field_texts)[0]
                    elif len(field_texts) > 1:
                        dict_[schema_element] = sorted(field_texts)
            else:
                field_text_arr = []
                for marc_field in marc_fields:
                    field_text_arr = field_text_arr + \
                        self.get_marc_field(*marc_field)
                field_text = ' '.join(field_text_arr)
                if strip_out:
                    field_text = re.sub(strip_out, '', field_text)
                if field_text:
                    dict_[schema_element] = field_text
        return dict_

    def __str__(self):
        """Return Schema.org data as a JSON-LD string.

        Returns:
            str
        """
        return json.dumps(
            self(),
            ensure_ascii=False,
            indent=4
        )


class SocSciMapsMarcXmlToEDM:
    """A class to convert MARCXML to  Europeana Data Model (EDM)."""

    # from Charles, via Slack (10/3/2019 9:52am)
    # For the TIFF image we also need a edm:WebResource. Ideally we would want
    # the original form of the metadata (whether .xml or .mrc), a ore:Proxy.

    # does everything get a dcterm:created predicate?
    # is edm:WebResource the same as ore:resourceMap?

    # Setting namespaces for subject, predicate, object values
    BASE = Namespace('http://ark.lib.uchicago.edu/ark:/61001/')
    EDM = Namespace('http://www.europeana.eu/schemas/edm/')
    ERC = Namespace('http://purl.org/kernel/elements/1.1/')
    MIX = Namespace('http://www.loc.gov/mix/v20/')
    OAI = Namespace('http://www.openarchives.org/OAI/2.0/')
    ORE = Namespace('http://www.openarchives.org/ore/terms/')
    PREMIS = Namespace('info:lc/xmlns/premis-v2/')
    VRA = Namespace('http://purl.org/vra/')

    def __init__(self, marcxml, master_file_metadata):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        self.dc = SocSciMapsMarcXmlToDc(marcxml)
        self.master_file_metadata = master_file_metadata

        if isinstance(self.dc.identifier, list):
            self.identifier = self.dc.identifier[0]
        else:
            self.identifier = self.dc.identifier

    def build_graph(self):
        self.short_id = self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')
        self.agg = URIRef('/aggregation/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.cho = URIRef('/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.pro = URIRef('/digital_collections/IIIF_Files/social_scientists_maps/{0}/{0}.dc.xml'.format(self.identifier.split('/').pop()))
        self.rem = URIRef('/rem/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.wbr = URIRef('/digital_collections/IIIF_Files/{}.tif'.format(self.short_id))

        self.graph = Graph()

        for sub in (self.rem, self.agg):
            if not bool(self.graph.query(
                prepareQuery('ASK { ?s ?p ?o . }'),
                initBindings={'s': sub}
            )):
                self.graph.set((
                    sub,
                    DCTERMS.created,
                    Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)
                ))

        for prefix, ns in (('dc', DC), ('dcterms', DCTERMS), ('edm', self.EDM),
			   ('erc', self.ERC), ('mix', self.MIX), 
                           ('ore', self.ORE), ('premis', self.PREMIS)):
            self.graph.bind(prefix, ns)

        self._build_aggregation()
        self._build_cho()
        self._build_proxy()
        self._build_resource_map() 
        self._build_web_resources()

    def _build_aggregation(self):
        self.graph.set((self.agg, RDF.type,                self.ORE.aggregation))
        self.graph.set((self.agg, DCTERMS.modified,        Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)))
        self.graph.set((self.agg, self.EDM.aggreatagedCHO, self.cho))
        self.graph.set((self.agg, self.EDM.dataProvider,   Literal("University of Chicago Library")))
        self.graph.set((self.agg, self.ORE.isDescribedBy,  self.cho))
        self.graph.set((self.agg, self.EDM.isShownAt,      Literal(self.identifier)))
        self.graph.set((self.agg, self.EDM.isShownBy,      Literal('IIIF URL for highest quality image of map')))
        self.graph.set((self.agg, self.EDM.object,         Literal('IIIF URL for highest quality image of map')))
        self.graph.set((self.agg, self.EDM.provider,       Literal('University of Chicago Library')))
        self.graph.set((self.agg, self.EDM.rights,         URIRef('https://rightsstatements.org/page/InC/1.0/?language=en')))

    def _build_cho(self):
        self.graph.set((self.cho, RDF.type, self.EDM.ProvidedCHO))

        for pre, obj_str in (
            (DC.coverage,     'dc:coverage'),
            (DC.creator,      'dc:creator'),
            (DC.date,         'dc:date'),
            (DC.description,  'dc:description'),
            (DC.extent,       'dc:extent'),
            (DC.identifier,   'dc:identifier'),
            (DC.language,     'dc:language'),
            (DC.publisher,    'dc:publisher'),
            (DC.rights,       'dc:rights'),
            (DC.subject,      'dc:subject'),
            (DC.title,        'dc:title'),
            (DC.type,         'dc:type'),
            (DCTERMS.spatial, 'dcterms:spatial'),
            (self.EDM.date,   'dc:date'),
            (self.ERC.what,   'dc:title'),
            (self.ERC.when,   'dc:date'),
            (self.ERC.who,    'dc:creator'),
        ):
            obj_str = obj_str.replace('dc:',      '{http://purl.org/dc/elements/1.1/}')
            obj_str = obj_str.replace('dcterms:', '{http://purl.org/dc/terms/}')

            for dc_obj_el in self.dc._asxml().findall(obj_str):
                try:
                    self.graph.set((self.cho, pre, Literal(dc_obj_el.text)))
                except AttributeError:
                    pass

        self.graph.set((self.cho, DCTERMS.isPartOf, Literal('pi-for-the-collection-in-wagtail')))
        self.graph.set((self.cho, self.EDM.currentLocation, Literal('Map Collection Reading Room (Room 370)')))
        self.graph.set((self.cho, self.EDM.type, Literal('IMAGE')))
        self.graph.set((self.cho, self.ERC.where, self.cho))

    def _build_proxy(self):
        self.graph.set((self.pro, RDF.type, self.ORE.proxy))
        self.graph.set((self.pro, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.set((self.pro, self.ORE.proxyFor, self.cho))
        self.graph.set((self.pro, self.ORE.proxyIn, self.agg))

    def _build_resource_map(self):
        self.graph.set((self.rem, DCTERMS.modified, Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)))
        self.graph.set((self.rem, DCTERMS.creator, URIRef('http://library.uchicago.edu/')))
        self.graph.set((self.rem, RDF.type, self.ORE.resourceMap))
        self.graph.set((self.rem, self.ORE.describes, self.agg))

    def _build_web_resources(self):
        for metadata in self.master_file_metadata:
            self.graph.set((self.wbr, RDF.type, self.EDM.WebResource))
            for p, o in (
                ('http://purl.org/dc/elements/1.1/format',            metadata['mime_type']),
                ('http://www.loc.gov/mix/v20/bitsPerSampleUnit',      'integer'),
                ('http://www.loc.gov/mix/v20/fileSize',               metadata['size']),
                ('http://www.loc.gov/mix/v20/formatName',             metadata['mime_type']),
                ('http://www.loc.gov/mix/v20/imageHeight',            metadata['height']),
                ('http://www.loc.gov/mix/v20/imageWidth',             metadata['width']),
                ('http://www.loc.gov/mix/v20/messageDigest',          metadata['md5']),
                ('http://www.loc.gov/mix/v20/messageDigestAlgorithm', 'MD5'),
                ('info:lc/xmlns/premis-v2/compositionLevel',          0),
                ('info:lc/xmlns/premis-v2/eventDateTime',             datetime.datetime.utcnow()),
                ('info:lc/xmlns/premis-v2/eventIdentifierType',       'ARK'),
                ('info:lc/xmlns/premis-v2/eventIdentifierValue',      '[NOID]'),
                ('info:lc/xmlns/premis-v2/eventType',                 'creation'),
                ('info:lc/xmlns/premis-v2/formatName',                metadata['mime_type']),
                ('info:lc/xmlns/premis-v2/messageDigest',             metadata['sha256']),
                ('info:lc/xmlns/premis-v2/messageDigestAlgorithm',    'SHA-256'),
                ('info:lc/xmlns/premis-v2/messageDigestOriginator',   '/sbin/sha256'),
                ('info:lc/xmlns/premis-v2/objectCategory',            'file'),
                ('info:lc/xmlns/premis-v2/objectIdentifierType',      'ARK'),
                ('info:lc/xmlns/premis-v2/objectIdentifierValue',     metadata['path']),
                ('info:lc/xmlns/premis-v2/originalName',              metadata['name']),
                ('info:lc/xmlns/premis-v2/size',                      metadata['size'])):
                self.graph.set((self.wbr, URIRef(p), Literal(o)))

    def __str__(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base=self.BASE).decode("utf-8")


class MarcXmlToOpenGraph(MarcXmlConverter):
    def __init__(self, marcxml):
        self.dc = MarcToDc(marcxml)
    def __str__(self):
        html = '\n'.join(('<meta property="og:title" content="{{ og_title }}" >',
                        '<meta property="og:type" content="{{ og_type }}" >',
                        '<meta property="og:url" content="{{ og_url }}" >',
                        '<meta property="og:image" content="{{ og_image }}" >',
                        '<meta property="og:description" content="{{ og_description }}" >',
                        '<meta property="og:site_name" content="{{ og_site_name }}" >'))
        return jinja2.Template(html).render(
            og_description=self.dc.description[0],
            og_image='image',
            og_site_name='site_name',
            og_title=self.dc.title[0],
            og_type='website',
            og_url='url'
        )


class MarcXmlToTwitterCard(MarcXmlConverter):
    def __init__(self, marcxml):
        self.dc = MarcToDc(marcxml)
    def __str__(self):
        html = '\n'.join(('<meta name="twitter:card" content="{{ twitter_card }}" >',
                          '<meta name="twitter:site" content="{{ twitter_site }}" >',
                          '<meta name="twitter:title" content="{{ twitter_title }}" >',
                          '<meta name="twitter:url" content="{{ twitter_url }}" >',
                          '<meta name="twitter:description" content="{{ twitter_description }}" >',
                          '<meta name="twitter:image" content="{{ twitter_image }}" >',
                          '<meta name="twitter:image:alt" content="{{ twitter_image_alt }}" >'))
        return jinja2.Template(html).render(
            twitter_card='card',
            twitter_description=self.dc.description[0],
            twitter_image='image',
            twitter_image_alt='image_alt',
            twitter_site='site',
            twitter_title=self.dc.title[0],
            twitter_url='url'
        )
