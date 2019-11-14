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

        self.short_id = self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')
        self.graph = Graph()
        for prefix, ns in (('dc', DC), ('dcterms', DCTERMS), ('edm', self.EDM),
			   ('erc', self.ERC), ('mix', self.MIX), 
                           ('ore', self.ORE), ('premis', self.PREMIS)):
            self.graph.bind(prefix, ns)


    def build_repository_triples(self):
        """Add triples for the repository itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        #repository_agg = URIRef('aggregation/repository.lib.uchicago.edu')
        repository_agg = URIRef('https://repository.lib.uchicago.edu/aggregation')
        repository_cho = URIRef('https://repository.lib.uchicago.edu')
        repository_pro = URIRef('https://repository.lib.uchicago.edu/index.dc.xml')
        #repository_rem = URIRef('rem/repository.lib.uchicago.edu')
        repository_rem = URIRef('https://repository.lib.uchicago.edu/rem')

        # aggregation for the repository
        self.graph.add((repository_agg, RDF.type,               self.ORE.Aggregation))
        self.graph.add((repository_agg, DCTERMS.created,        now))
        self.graph.add((repository_agg, DCTERMS.modified,       now))
        self.graph.add((repository_agg, self.EDM.aggregatedCHO, repository_cho))
        self.graph.add((repository_agg, self.EDM.dataProvider,  Literal("The University of Chicago Library")))
        self.graph.add((repository_agg, self.EDM.isShownAt,     URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((repository_agg, self.EDM.provider,      Literal("The University of Chicago Library")))
        self.graph.add((repository_agg, self.EDM.rights,        URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((repository_agg, self.ORE.isDescribedBy, repository_rem))

        # cultural heritage object for the repository
        self.graph.add((repository_cho, RDF.type,               self.EDM.ProvidedCHO))
        self.graph.add((repository_cho, DC.coverage,            URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((repository_cho, DC.coverage,            Literal('World')))
        self.graph.add((repository_cho, DC.creator,             Literal('The University of Chicago Library')))
        self.graph.add((repository_cho, DC.date,                Literal('2006')))
        self.graph.add((repository_cho, DC.description,         Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((repository_cho, DC.identifier,          URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((repository_cho, DC.rights,              URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((repository_cho, DC.title,               Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((repository_cho, DC.type,                Literal('Collection')))
        self.graph.add((repository_cho, DCTERMS.hasPart,        URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((repository_cho, DCTERMS.hasPart,        URIRef('https://repository.lib.uchicago.edu/specialcollections')))
        self.graph.add((repository_cho, self.EDM.type,          Literal('COLLECTION')))
        self.graph.add((repository_cho, self.EDM.year,          Literal('2006'))) 
        self.graph.add((repository_cho, self.ERC.what,          Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((repository_cho, self.ERC.when,          Literal('2006')))
        self.graph.add((repository_cho, self.ERC.where,         repository_cho))
        self.graph.add((repository_cho, self.ERC.who,           Literal('The University of Chicago Library')))

        # proxy for the repository
        self.graph.add((repository_pro, RDF.type,               self.ORE.Proxy))
        self.graph.add((repository_pro, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((repository_pro, self.ORE.proxyFor,      repository_cho))
        self.graph.add((repository_pro, self.ORE.proxyIn,       repository_agg))

        # resource map for the repository
        self.graph.add((repository_rem, RDF.type,               self.ORE.ResourceMap))
        self.graph.add((repository_rem, DCTERMS.created,        now))
        self.graph.add((repository_rem, DCTERMS.modified,       now))
        self.graph.add((repository_rem, DCTERMS.creator,        repository_cho))
        self.graph.add((repository_rem, self.ORE.describes,     repository_agg))

    def build_digital_collections_triples(self):
        """Add triples for digital collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        #digcol_agg = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections')
        digcol_agg = URIRef('https://repository.lib.uchicago.edu/digitalcollections/Aggregation')
        digcol_cho = URIRef('https://repository.lib.uchicago.edu/digitalcollections')
        digcol_pro = URIRef('https://repository.lib.uchicago.edu/digitalcollections/index.dc.xml')
        #digcol_rem = URIRef('rem/repository.lib.uchicago.edu/digitalcollections')
        digcol_rem = URIRef('https://repository.lib.uchicago.edu/digitalcollections/rem')

        # aggregation for digital collections
        self.graph.add((digcol_agg, RDF.type,               self.ORE.ResourceMap))
        self.graph.add((digcol_agg, DCTERMS.created,        now))
        self.graph.add((digcol_agg, DCTERMS.modified,       now))
        self.graph.add((digcol_agg, self.EDM.aggregatedCHO, URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((digcol_agg, self.EDM.dataProvider,  Literal('The University of Chicago Library')))
        self.graph.add((digcol_agg, self.EDM.isShownAt,     URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((digcol_agg, self.EDM.provider,      Literal('The University of Chicago Library')))
        self.graph.add((digcol_agg, self.EDM.rights,        URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((digcol_agg, self.ORE.isDescribedBy, digcol_rem))

        # cultural heritage object for digital collections
        self.graph.add((digcol_cho, RDF.type,               self.EDM.ProvidedCHO))
        self.graph.add((digcol_cho, DC.coverage,            URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((digcol_cho, DC.coverage,            Literal('World')))
        self.graph.add((digcol_cho, DC.creator,             Literal('The University of Chicago Library')))
        self.graph.add((digcol_cho, DC.date,                Literal('2006')))
        self.graph.add((digcol_cho, DC.description,         Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((digcol_cho, DC.identifier,          URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((digcol_cho, DC.rights,              URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((digcol_cho, DC.title,               Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((digcol_cho, DC.type,                Literal('Collection')))
        self.graph.add((digcol_cho, DCTERMS.hasPart,        URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((digcol_cho, DCTERMS.isPartOf,       URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((digcol_cho, self.EDM.type,          Literal('COLLECTION')))
        self.graph.add((digcol_cho, self.EDM.year,          Literal('2014')))
        self.graph.add((digcol_cho, self.ERC.what,          Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((digcol_cho, self.ERC.when,          Literal('2014')))
        self.graph.add((digcol_cho, self.ERC.where,         URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((digcol_cho, self.ERC.who,           Literal('The University of Chicago Library')))

        # proxy for digital collections
        self.graph.add((digcol_pro, RDF.type,                self.ORE.Proxy))
        self.graph.add((digcol_pro, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((digcol_pro, self.ORE.proxyFor,       digcol_cho))
        self.graph.add((digcol_pro, self.ORE.proxyIn,        digcol_agg))

        # resource map for digital collections.
        self.graph.add((digcol_rem, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((digcol_rem, DCTERMS.created,         now))
        self.graph.add((digcol_rem, DCTERMS.modified,        now))
        self.graph.add((digcol_rem, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((digcol_rem, self.ORE.describes,      digcol_agg))

    def build_map_collection_triples(self):
        """Add triples for the map collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        #mapcol_agg = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections/maps')
        mapcol_agg = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/aggregation')
        mapcol_cho = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')
        mapcol_pro = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/index.dc.xml')
        #mapcol_rem = URIRef('rem/repository.lib.uchicago.edu/digitalcollections/maps')
        mapcol_rem = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/rem')

        # aggregation for the map collection
        self.graph.add((mapcol_agg, RDF.type,                self.ORE.Aggregation))
        self.graph.add((mapcol_agg, DCTERMS.created,         now))
        self.graph.add((mapcol_agg, DCTERMS.modified,        now))
        self.graph.add((mapcol_agg, self.EDM.aggregatedCHO,  URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((mapcol_agg, self.EDM.dataProvider,   Literal('The University of Chicago Library')))
        self.graph.add((mapcol_agg, self.EDM.isShownAt,      mapcol_cho))
        self.graph.add((mapcol_agg, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((mapcol_agg, self.EDM.rights,         URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((mapcol_agg, self.ORE.isDescribedBy,  mapcol_rem))

        # cultural heritage object for the map collection
        self.graph.add((mapcol_cho, RDF.type,                self.EDM.ProvidedCHO))
        self.graph.add((mapcol_cho, DC.coverage,             URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((mapcol_cho, DC.coverage,             Literal('World')))
        self.graph.add((mapcol_cho, DC.creator,              Literal('The University of Chicago Library')))
        self.graph.add((mapcol_cho, DC.date,                 Literal('2006')))
        self.graph.add((mapcol_cho, DC.description,          Literal('The University of Chicago Library Map Collection')))
        self.graph.add((mapcol_cho, DC.identifier,           URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((mapcol_cho, DC.rights,               URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((mapcol_cho, DC.title,                Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((mapcol_cho, DC.type,                 Literal('Collection')))
        self.graph.add((mapcol_cho, DCTERMS.hasPart,         URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((mapcol_cho, DCTERMS.isPartOf,        URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((mapcol_cho, self.EDM.type,           Literal('COLLECTION')))
        self.graph.add((mapcol_cho, self.EDM.year,           Literal('2014')))
        self.graph.add((mapcol_cho, self.ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((mapcol_cho, self.ERC.when,           Literal('2014')))
        self.graph.add((mapcol_cho, self.ERC.where,          URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((mapcol_cho, self.ERC.who,            Literal('The University of Chicago Library')))

        # proxy for the map collection
        self.graph.add((mapcol_pro, RDF.type,                self.ORE.Proxy))
        self.graph.add((mapcol_pro, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((mapcol_pro, self.ORE.proxyFor,       mapcol_cho))
        self.graph.add((mapcol_pro, self.ORE.proxyIn,        mapcol_agg))

        # resource map for the map collection 
        self.graph.add((mapcol_rem, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((mapcol_rem, DCTERMS.created,         now))
        self.graph.add((mapcol_rem, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((mapcol_rem, DCTERMS.modified,        now))
        self.graph.add((mapcol_rem, self.ORE.describes,      mapcol_agg))

    def build_socscimap_collection_triples(self):
        """Add triples for the social scientist map collection, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        #ssmaps_agg = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
        ssmaps_agg = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/aggregation')
        ssmaps_cho = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
        ssmaps_pro = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/index.dc.xml')
        #ssmaps_rem = URIRef('rem/repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
        ssmaps_rem = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/rem')

        # aggregation for the social scientist maps collection
        self.graph.add((ssmaps_agg, RDF.type,                self.ORE.Aggregation))
        self.graph.add((ssmaps_agg, DCTERMS.created,         now))
        self.graph.add((ssmaps_agg, DCTERMS.modified,        now))
        self.graph.add((ssmaps_agg, self.EDM.aggregatedCHO,  URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((ssmaps_agg, self.EDM.dataProvider,   Literal('The University of Chicago Library')))
        self.graph.add((ssmaps_agg, self.EDM.isShownAt,      ssmaps_cho))
        self.graph.add((ssmaps_agg, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((ssmaps_agg, self.EDM.rights,         URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((ssmaps_agg, self.ORE.isDescribedBy,  ssmaps_rem))

        # cultural heritage object for the social scientist maps collection
        self.graph.add((ssmaps_cho, RDF.type,                self.EDM.ProvidedCHO))
        self.graph.add((ssmaps_cho, DC.coverage,             URIRef('https://vocab.getty.edu/page/tgn/7013596')))
        self.graph.add((ssmaps_cho, DC.coverage,             Literal('Chicago')))
        self.graph.add((ssmaps_cho, DC.creator,              Literal('The University of Chicago Library')))
        self.graph.add((ssmaps_cho, DC.date,                 Literal('2006')))
        self.graph.add((ssmaps_cho, DC.description,          Literal('The University of Chicago Library Social Scientists Map Collection')))
        self.graph.add((ssmaps_cho, DC.identifier,           URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((ssmaps_cho, DC.rights,               URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((ssmaps_cho, DC.title,                Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((ssmaps_cho, DC.type,                 Literal('Collection')))
        self.graph.add((ssmaps_cho, DCTERMS.isPartOf,        URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((ssmaps_cho, self.EDM.type,           Literal('COLLECTION')))
        self.graph.add((ssmaps_cho, self.EDM.year,           Literal('2014')))
        self.graph.add((ssmaps_cho, self.ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((ssmaps_cho, self.ERC.when,           Literal('2014')))
        self.graph.add((ssmaps_cho, self.ERC.where,          URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((ssmaps_cho, self.ERC.who,            Literal('The University of Chicago Library')))

        # proxy for the social scientists maps collection
        self.graph.add((ssmaps_pro, RDF.type,                self.ORE.Proxy))
        self.graph.add((ssmaps_pro, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((ssmaps_pro, self.ORE.proxyFor,       ssmaps_cho))
        self.graph.add((ssmaps_pro, self.ORE.proxyIn,        ssmaps_agg))

        # resource map for the social scientists map collection
        self.graph.add((ssmaps_rem, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((ssmaps_rem, DCTERMS.created,         now))
        self.graph.add((ssmaps_rem, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((ssmaps_rem, self.ORE.describes,      ssmaps_agg))

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
        agg = URIRef('/aggregation/digital_collections/IIIF_Files{}'.format(self.short_id))
        cho = URIRef('/digital_collections/IIIF_Files{}'.format(self.short_id))
        pro = URIRef('/digital_collections/IIIF_Files/social_scientists_maps/{0}/{0}.dc.xml'.format(self.identifier.split('/').pop()))
        rem = URIRef('/rem/digital_collections/IIIF_Files{}'.format(self.short_id))
        wbr = URIRef('/digital_collections/IIIF_Files/{}.tif'.format(self.short_id))

        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation for the item.
        self.graph.add((agg, RDF.type,                self.ORE.Aggregation))
        self.graph.add((agg, DCTERMS.created,         now))
        self.graph.add((agg, DCTERMS.modified,        now))
        self.graph.add((agg, self.EDM.aggreatagedCHO, cho))
        self.graph.add((agg, self.EDM.dataProvider,   Literal("The University of Chicago Library")))
        self.graph.add((agg, self.ORE.isDescribedBy,  cho))
        self.graph.add((agg, self.EDM.isShownAt,      Literal(self.identifier)))
        self.graph.add((agg, self.EDM.isShownBy,      Literal('IIIF URL for highest quality image of map')))
        self.graph.add((agg, self.EDM.object,         Literal('IIIF URL for highest quality image of map')))
        self.graph.add((agg, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((agg, self.EDM.rights,         URIRef('https://rightsstatements.org/page/InC/1.0/?language=en')))

        self._build_cho(cho)

        # proxy for the item.
        self.graph.add((pro,      RDF.type,           self.ORE.Proxy))
        self.graph.add((pro,      URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((pro,      self.ORE.proxyFor,  cho))
        self.graph.add((pro,      self.ORE.proxyIn,   agg))

        # resource map for the item.
        self.graph.add((rem,      DCTERMS.created,    Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)))
        self.graph.add((rem,      DCTERMS.modified,   Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)))
        self.graph.add((rem,      DCTERMS.creator,    URIRef('http://library.uchicago.edu')))
        self.graph.add((rem,      RDF.type,           self.ORE.ResourceMap))
        self.graph.add((rem,      self.ORE.describes, agg))

        self._build_web_resources(wbr)

        # connect the item to its collection.
        self.graph.add((URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc'), DCTERMS.hasPart, cho))

    def _build_cho(self, cho):
        """The cultural herigate object is the map itself. 

        This method adds triples that describe the cultural heritage object.

        Args:
            agg (URIRef): aggregation 
            cho (URIRef): cultural heritage object

        Side Effect:
            Add triples to self.graph
        """
        self.graph.add((cho, RDF.type, self.EDM.ProvidedCHO))
        for pre, obj_str in (
            (DC.coverage,     '{http://purl.org/dc/elements/1.1/}coverage'),
            (DC.creator,      '{http://purl.org/dc/elements/1.1/}creator'),
            (DC.date,         '{http://purl.org/dc/elements/1.1/}date'),
            (DC.description,  '{http://purl.org/dc/elements/1.1/}description'),
            (DC.extent,       '{http://purl.org/dc/elements/1.1/}extent'),
            (DC.identifier,   '{http://purl.org/dc/elements/1.1/}identifier'),
            (DC.language,     '{http://purl.org/dc/elements/1.1/}language'),
            (DC.publisher,    '{http://purl.org/dc/elements/1.1/}publisher'),
            (DC.rights,       '{http://purl.org/dc/elements/1.1/}rights'),
            (DC.subject,      '{http://purl.org/dc/elements/1.1/}subject'),
            (DC.title,        '{http://purl.org/dc/elements/1.1/}title'),
            (DC.type,         '{http://purl.org/dc/elements/1.1/}type'),
            (DCTERMS.spatial, '{http://purl.org/dc/terms/}spatial'),
            (self.EDM.date,   '{http://purl.org/dc/elements/1.1/}date'),
            (self.ERC.what,   '{http://purl.org/dc/elements/1.1/}title'),
            (self.ERC.when,   '{http://purl.org/dc/elements/1.1/}date'),
            (self.ERC.who,    '{http://purl.org/dc/elements/1.1/}creator'),
        ):
            for dc_obj_el in self.dc._asxml().findall(obj_str):
                try:
                    self.graph.add((self.cho, pre, Literal(dc_obj_el.text)))
                except AttributeError:
                    pass

        self.graph.add((cho, DCTERMS.isPartOf, URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((cho, self.EDM.currentLocation, Literal('Map Collection Reading Room (Room 370)')))
        self.graph.add((cho, self.EDM.type, Literal('IMAGE')))
        self.graph.add((cho, self.ERC.where, cho))

    def _build_web_resources(self, wbr):
        for metadata in self.master_file_metadata:
            self.graph.add((wbr, RDF.type, self.EDM.WebResource))
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
                self.graph.add((wbr, URIRef(p), Literal(o)))

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
