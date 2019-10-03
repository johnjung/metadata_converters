import datetime
import json
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


class MarcToDc(MarcXmlConverter):
    """
    A class to convert MARCXML to Dublin Core. 

    The Library of Congress MARCXML to DC conversion is here:
    http://www.loc.gov/standards/marcxml/xslt/MARC21slim2SRWDC.xsl
    It produces slightly different results. 

    mappings -- a list of tuples-
        [0] -- Dublin Core metadata element.
        [1] -- a list-
            [0] a boolean, DC element is repeatable. 
            [1] a list, a MARC field specification-
                [0] a string, the MARC field itself.
                [1] a regular expression (as a string), allowable subfields. 
                [2] a regular expression (as a string), indicator 1.
                [3] a regular expression (as a string), indicator 2. 
        [2] a boolean, subfields each get their own DC element. If False,
            subfields are joined together into a single DC element.
            assert this field==False if [0]==False.
        [3] a regular expression (as a string) to strip out of the field, or
            None if there is nothing to exclude.
            if the resulting value is '' it won't be added.

    """

    mappings = [
        ('DC.rights.access',         [False, [('506', '[a-z]',  '.', '.')], False,   None]),
        ('DC.contributor',           [True,  [('700', 'a',      '.', '.'),
                                              ('710', 'a',      '.', '.')], False,   None]),
        ('DC.coverage',              [False, [('255', '[a-z]',  '.', '.')], False,   None]),
        ('DC.creator',               [True,  [('100', '[a-z]',  '.', '.'),
                                              ('110', '[a-z]',  '.', '.'),
                                              ('111', '[a-z]',  '.', '.'),
                                              ('245', 'c',      '.', '.')], False,   None]),
        ('DC.date.copyrighted',      [True,  [('264', 'c',      '.', '4')], False,   None]),
        ('DC.description',           [False, [('300', '[a-z3]', '.', '.')], False,   None]),
        ('DC.format.extent',         [False, [('300', '[a-z]',  '.', '.')], False,   None]),
        ('DC.format',                [True,  [('337', 'a',      '.', '.')], False,   '^computer$']),
        ('DC.relation.hasFormat',    [True,  [('533', 'a',      '.', '.')], False,   None]),
        ('DC.identifier',            [True,  [('020', '[a-z]',  '.', '.'),
                                              ('021', '[a-z]',  '.', '.'),
                                              ('022', '[a-z]',  '.', '.'),
                                              ('023', '[a-z]',  '.', '.'),
                                              ('024', '[a-z]',  '.', '.'),
                                              ('025', '[a-z]',  '.', '.'),
                                              ('026', '[a-z]',  '.', '.'),
                                              ('027', '[a-z]',  '.', '.'),
                                              ('028', '[a-z]',  '.', '.'),
                                              ('029', '[a-z]',  '.', '.'),
                                              ('856', 'u',      '.', '.')], False,   None]),
        ('DC.relation.isPartOf',     [True,  [('490', '[a-z]',  '.', '.'),
                                              ('533', 'f',      '.', '.'),
                                              ('700', 't',      '.', '.'),
                                              ('830', '[a-z]',  '.', '.')], False,   None]),
        ('DC.date.issued',           [True,  [('264', 'c',      '1', '.')], False,   None]),
        ('DC.language',              [True,  [('041', '[a-z]',  '.', '.')], True,    None]),
        ('DC.coverage.location',     [True,  [('264', 'a',      '1', '.'),
                                              ('533', 'b',      '.', '.')], False,   None]),
        ('DC.format.medium',         [True,  [('338', 'a',      '.', '.')], False,   None]),
        ('DC.coverage.periodOfTime', [True,  [('650', 'y',      '.', '.')], False,   None]),
        ('DC.publisher',             [True,  [('264', 'b',      '1', '.')], False,   None]),
        ('DC.relation',              [True,  [('730', 'a',      '.', '.')], False,   None]),
        ('DC.subject',               [True,  [('050', '[a-z]',  '.', '.')], False,   '[. ]*$']),
        ('DC.subject',               [True,  [('650', '[ax]',   '.', '.')], True,    '[. ]*$']),
        ('DC.title',                 [True,  [('130', '[a-z]',  '.', '.'),
                                              ('240', '[a-z]',  '.', '.'),
                                              ('245', '[ab]',   '.', '.'),
                                              ('246', '[a-z]',  '.', '.')], False,   None]),
        ('DC.type',                  [True,  [('336', 'a',      '.', '.'),
                                              ('650', 'v',      '.', '.'),
                                              ('651', 'v',      '.', '.'),
                                              ('655', 'a',      '.', '.')], False,   '^Maps[. ]*$|[. ]*$'])
    ]

    def __init__(self, marcxml):
        """Initialize an instance of the class MarcToDc.

        Args:
            marcxml (str): a marcxml collection with a single record.
        """
        for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
            if repeat_dc == False:
                assert repeat_sf == False
        super().__init__(marcxml)
        self._build_xml()

    def __getattr__(self, attr):
        """Return individual Dublin Core elements as instance properties, e.g.
        self.identifier.

        Returns:
            list
        """
        vals = [e.text for e in self.dc.findall('{{http://purl.org/dc/elements/1.1/}}{}'.format(attr.replace('_','.')))]   
        return sorted(vals)

    def todict(self):
        """Return a dictionary/list/etc. of metadata elements, for display in
        templates."""
        raise NotImplementedError

    def _build_xml(self):
        ElementTree.register_namespace(
            'dc', 'http://purl.org/dc/elements/1.1/')

        metadata = ElementTree.Element('metadata')
        for dc_element, (repeat_dc, marc_fields, repeat_sf, strip_out) in self.mappings:
            if repeat_dc:
                field_texts = set()
                if repeat_sf:
                    for marc_field in marc_fields:
                        for field_text in self.get_marc_field(*marc_field):
                            if strip_out:
                                field_text = re.sub(strip_out, '', field_text)
                            if field_text:
                                field_texts.add(field_text)
                    for field_text in field_texts:
                        ElementTree.SubElement(
                            metadata,
                            dc_element.replace(
                                'DC.', '{http://purl.org/dc/elements/1.1/}')
                        ).text = field_text
                else:
                    for marc_field in marc_fields:
                        field_text = ' '.join(self.get_marc_field(*marc_field))
                        if strip_out:
                            field_text = re.sub(strip_out, '', field_text)
                        if field_text:
                            field_texts.add(field_text)
                    for field_text in field_texts:
                        ElementTree.SubElement(
                            metadata,
                            dc_element.replace(
                                'DC.', '{http://purl.org/dc/elements/1.1/}')
                        ).text = field_text
            else:
                field_text_arr = []
                for marc_field in marc_fields:
                    field_text_arr = field_text_arr + \
                        self.get_marc_field(*marc_field)
                field_text = ' '.join(field_text_arr)
                if strip_out:
                    field_text = re.sub(strip_out, '', field_text)
                if field_text:
                    ElementTree.SubElement(
                        metadata,
                        dc_element.replace(
                            'DC.', '{http://purl.org/dc/elements/1.1/}')
                    ).text = field_text
        self.dc = metadata

    def __str__(self):
        """Return Dublin Core XML as a string.

        Returns:
            str
        """
        def indent(elem, level=0):
            i = "\n" + level * "  "
            j = "\n" + (level - 1) * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for subelem in elem:
                    indent(subelem, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = j
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = j
            return elem

        indent(self.dc)
        return ElementTree.tostring(self.dc, 'utf-8', method='xml').decode('utf-8')


class SocSciMapsMarcToDc(MarcToDc):

    # another mappings table maps DC elements to functions.
    # special function names automatically get called and their data gets appended. 

    mappings = [
        ('DC.creator',     [True , [('100', '[a-z]', '.', '.')], False, None]),
        ('DC.extent',      [False, [('300', 'c',     '.', '.')], False, None]),
        ('DC.description', [False, [('500', '[a-z]', '.', '.')], False, None]),
        ('DC.identifier',  [False, [('865', 'u',     '.', '.')], False, None]),
        ('DC.title',       [False, [('245', '[a-z]', '.', '.')], False, None]), 
        ('DC.type',        [False, [('336', 'a',     '.', '.')], False, None])
    ]

    def _get_coverage(self):
        values = []
        for element in self.record:
            if not element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                continue
            if not element.attrib['tag'] == '651':
                continue
            if not element.attrib['ind2'] == '7':
                continue
            keep_subfields = False
            for subfield in element:
                if subfield.attrib['code'] == '2' and not subfield.text == 'fast':
                    keep_subfields = True
            if keep_subfields:
                for subfield in element:
                    if re.match('[a-z]', subfield.attrib['code']):
                        values.append(subfield.text)
        return ('DC.coverage', values)

    def _date_or_publisher(self, subfield_code):
        for element in self.record:
            if not element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                continue
            for tag in ('260', '264'):
                if element.attrib['tag'] == tag:
                    for subfield in element:
                        if subfield.attrib['code'] == subfield_code:
                            return subfield.text
        return ''

    def _get_date(self):
        return ('DC.date', self._date_or_publisher('c'))

    def _get_language(self):
        return ('DC.language', 'en')

    def _get_publisher(self):
        return ('DC.publisher', self._date_or_publisher('b'))


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


class SocSciMapsMarcXmlToEDM(SocSciMapsMarcToDc):
    """A class to convert MARCXML to  Europeana Data Model (EDM)."""

    # Setting namespaces for subject, predicate, object values
    VRA = Namespace('http://purl.org/vra/')
    OAI = Namespace('http://www.openarchives.org/OAI/2.0/')
    ORE = Namespace('http://www.openarchives.org/ore/terms/')
    ERC = Namespace('http://purl.org/kernel/elements/1.1/')
    EDM = Namespace('http://www.europeana.eu/schemas/edm/')
    BASE = Namespace('http://ark.lib.uchicago.edu/ark:/61001/')

    def __init__(self, marcxml):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        super().__init__(marcxml)

        if isinstance(self.identifier, list):
            self.identifier = self.identifier[0]

        self.graph = Graph()
        self.graph.bind('dc', DC)
        self.graph.bind('edm', self.EDM)
        self.graph.bind('dcterms', DCTERMS)
        self.graph.bind('ore', self.ORE)
        self._build_graph()

    def _build_graph(self):
        resource_map = URIRef('/rem/digital_collections/IIIF_Files{}'.format(
            self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')
        ))

	# check to see if the resource map node exists before adding a creation
	# date.
        if not bool(self.graph.query(
            prepareQuery('ASK { ?s ?p ?o . }'),
            initBindings={'s': resource_map}
        )):
            self.graph.set((
                resource_map,
                DCTERMS.created,
                Literal(datetime.datetime.utcnow(), datatype=XSD.date)
            ))

        self.graph.add((
            resource_map,
            DCTERMS.modified,
            Literal(datetime.datetime.utcnow(), datatype=XSD.date)
        ))

        self.graph.set((
            resource_map,
            DCTERMS.creator,
            URIRef('http://library.uchicago.edu/')
        ))

        self.graph.set((
            resource_map,
            RDF.type,
            self.ORE.resourceMap
        ))

        # aggregation

        aggregation = URIRef('/aggregation/digital_collections/IIIF_Files{}'.format(
            self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')
        ))
        cultural_heritage_object = URIRef('/digital_collections/IIIF_Files{}'.format(
            self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')
        ))

        if not bool(self.graph.query(
            prepareQuery('ASK { ?s ?p ?o . }'),
            initBindings={'s': aggregation}
        )):
            self.graph.add((
                aggregation,
                DCTERMS.created,
                Literal(datetime.datetime.utcnow(), datatype=XSD.date)
            ))

        self.graph.add((
            aggregation,
            DCTERMS.modified,
            Literal(datetime.datetime.utcnow(), datatype=XSD.date)
        ))

        self.graph.set((
            resource_map,
            self.ORE.describes,
            aggregation
        ))

        self.graph.add((
            aggregation,
            DCTERMS.modified,
            Literal(datetime.datetime.utcnow(), datatype=XSD.date)
        ))

        self.graph.add((
            aggregation,
            self.EDM.aggreatagedCHO,
            cultural_heritage_object
        ))

        self.graph.add((
            aggregation,
            self.EDM.dataProvider,
            Literal("University of Chicago Library")
        ))

        self.graph.add((
            aggregation,
            self.EDM.isShownAt,
            Literal(self.identifier)
        ))

        '''
        self.graph.add((
            aggregation,
            self.EDM.isShownBy,
            Literal('IIIF URL for highest quality image of map')
        ))

        self.graph.add((
            aggregation,
            self.EDM.object,
            Literal('IIIF URL for highest quality image of map')
        ))
        '''

        self.graph.add((
            aggregation,
            self.EDM.provider,
            Literal('University of Chicago Library')
        ))

        self.graph.add((
            aggregation,
            self.EDM.rights,
            URIRef('https://rightsstatements.org/page/InC/1.0/?language=en')
        ))

        self.graph.set((
            aggregation,
            self.ORE.isDescribedBy,
            cultural_heritage_object
        ))

        self.graph.set((
            aggregation,
            RDF.type,
            self.ORE.aggregation
        ))
 
        # cultural_heritage_object

        self.graph.set((
            cultural_heritage_object,
            RDF.type,
            self.EDM.ProvidedCHO
        ))

        for p, o_element_str in (
            (DC.title, '{http://purl.org/dc/elements/1.1/}title'),
            (DC.description, '{http://purl.org/dc/elements/1.1/}description'),
            (DC.language, '{http://purl.org/dc/elements/1.1/}language'),
            (DC.subject, '{http://purl.org/dc/elements/1.1/}subject'),
            (DC.type, '{http://purl.org/dc/elements/1.1/}type'),
            (DC.coverage, '{http://purl.org/dc/elements/1.1/}coverage'),
            (DCTERMS.spatial, '{http://purl.org/dc/terms/}spatial')
        ):
            try:
                self.graph.add((
                    cultural_heritage_object,
                    p,
                    Literal(self.dc.find(o_element_str).text)
                ))
            except AttributeError:
                pass

    def __str__(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base=self.BASE).decode("utf-8")
