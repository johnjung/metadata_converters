import datetime, getpass, hashlib, jinja2, json, magic, os, \
       pymarc, re, string, sys
import xml.etree.ElementTree as ElementTree

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, FOAF, DC, DCTERMS, XSD
from rdflib.plugins.sparql import prepareQuery

def remove_marc_punctuation(s):
    s = re.sub('^\s*', '', s)
    s = re.sub('[ .,:;]*$', '', s)
    if s[0] == '[' and s[-1] == ']':
        s = s[1:-1]
    return s

def convert_034_coords_to_marc_rda(s):
    s = s.split(' ')
    return "$$c({} {}°{}'{}\"-{} {}°{}'{}\"/{} {}°{}'{}\"-{} {}°{}'{}\")".format(
        s[0][0],
        s[0][1:4].lstrip('0'),
        s[0][4:6],
        s[0][6:8],
        s[1][0],
        s[1][1:4].lstrip('0'),
        s[1][4:6],
        s[1][6:8],
        s[2][0],
        s[2][1:4].lstrip('0'),
        s[2][4:6],
        s[2][6:8],
        s[3][0],
        s[3][1:4].lstrip('0'),
        s[3][4:6],
        s[3][6:8]
    )

# Subfields $d, $e, $f, and $g always appear together. The coordinates may be recorded in the form hdddmmss (hemisphere-degrees-minutes-seconds), however, other forms are also allowed, such as decimal degrees. The subelements are each right justified and unused positions contain zeros.

# $$c(E 5°57'00"-E 10°29'00"/N 47°48'00"-N 45°49'00")
# W0875104 W0873125 N0420123 N0413839

def list_is_a_subset_of_lists(l, lists_to_check):
    for lst in lists_to_check:
        if set(l).issubset(set(lst)):
            return True
    return False

def remove_subsets(list_of_lists):
    list_of_lists = sorted(list_of_lists, key=lambda l: len(l), reverse=True)

    i = len(list_of_lists) - 1
    while i >= 0:
        if len(list_of_lists[i]) == 0:
            del list_of_lists[i]
        elif list_is_a_subset_of_lists(list_of_lists[i], list_of_lists[0:i]):
            del list_of_lists[i]
        i -= 1

    return list_of_lists

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

def pairwise(iterable):
    iterable = iter(iterable)
    while True:
        try:
            yield next(iterable), next(iterable)
        except StopIteration:
            break

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


class MarcXmlToDc:
    def __init__(self, digital_record, print_record):
        """
            digital_record_id: identifier for the digital record.
        """
        self.digital_record = digital_record
        self.print_record = print_record

        ElementTree.register_namespace(
            'bf', 'http://id.loc.gov/ontologies/bibframe/')
        ElementTree.register_namespace(
            'dc', 'http://purl.org/dc/elements/1.1/')
        ElementTree.register_namespace(
            'dcterms', 'http://purl.org/dc/terms/')
        ElementTree.register_namespace(
            'mods', 'http://www.loc.gov/mods/v3/')

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
        def process_subject(s):
            if s[-1] == '.':
                return s[:-1]
            else:
                return s

        metadata = ElementTree.Element('metadata')

        # bf:Local
        ElementTree.SubElement(
            metadata,
            '{http://id.loc.gov/ontologies/bibframe/}Local'
        ).text = 'http://pi.lib.uchicago.edu/1001/cat/bib/{}'.format(
            self.print_record['001'].value()
        )

        # bf:ClassificationLcc
        ElementTree.SubElement(
            metadata,
            '{http://id.loc.gov/ontologies/bibframe/}ClassificationLcc'
        ).text = self.print_record['929']['a']

        # bf:coordinates
        coordinates = []
        for f in self.digital_record.get_fields('034'):
            for sf in f.get_subfields('d', 'e', 'f', 'g'):
                coordinates.append(sf)
        if coordinates: 
            ElementTree.SubElement(
                metadata,
                '{http://id.loc.gov/ontologies/bibframe/}coordinates'
            ).text = convert_034_coords_to_marc_rda(
                ' '.join(coordinates)
            )

        # dcterms:accessRights
        for f in self.digital_record.get_fields('506'):
            sf = f.get_subfields(*list(string.ascii_lowercase))
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}accessRights'
                ).text = ' '.join(sf)

        # dcterms:alternative
        for f in self.digital_record.get_fields('246'):
            sf = f.get_subfields(*list(string.ascii_lowercase))
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}alternative'
                ).text = ' '.join(sf)

        # dc:contributor
        for f in self.digital_record.get_fields('700'):
            if f['t'] is None:
                for sf in f.get_subfields('a'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}contributor'
                    ).text = remove_marc_punctuation(sf)

        for f in self.digital_record.get_fields('710'):
            for sf in f.get_subfields('a'):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/elements/1.1/}contributor'
                ).text = remove_marc_punctuation(sf)

        # dc:coverage
        for f in self.digital_record.get_fields('651'):
            if f.indicator2 == '7' and f['2'] == 'fast':
                for sf in f.get_subfields('a'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}coverage'
                    ).text = remove_marc_punctuation(sf)

        # dc:creator
        for n in ('100', '110', '111'):
            for f in self.digital_record.get_fields(n):
                sf = f.get_subfields(*list(string.ascii_lowercase))
                if sf:
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}creator'
                    ).text = remove_marc_punctuation(
                        ' '.join(sf)
                    )

        # dcterms:dateCopyrighted
        for f in self.digital_record.get_fields('264'):
            if f.indicator2 == '4':
                for sf in f.get_subfields('c'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/terms/}dateCopyrighted'
                    ).text = sf

        # dc:description
        for n in ('500', '538'):
            for f in self.digital_record.get_fields(n):
                sf = f.get_subfields(*list(string.ascii_lowercase))
                if sf:
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}description'
                    ).text = ' '.join(sf)

        # dc:format
        formats = set()
        for f in self.digital_record.get_fields('255'):
            for sf in f.get_subfields('a', 'b'):
                formats.add(sf)
        for f in self.print_record.get_fields('300'):
            for sf in f.get_subfields('a', 'c'):
                formats.add(sf)
        for f in sorted(list(formats)):
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}format'
            ).text = remove_marc_punctuation(f)

        # dcterms:hasFormat
        for f in self.digital_record.get_fields('776'):
            for sf in f.get_subfields('i'):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}hasFormat'
                ).text = remove_marc_punctuation(sf)

        if self.digital_record['856']['u'] is not None:
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}identifier'
            ).text = self.digital_record['856']['u']

        # bf:ISBN
        for n in ('020'):
            for f in self.digital_record.get_fields(n):
                for sf in f.get_subfields(*list(string.ascii_lowercase)):
                    ElementTree.SubElement(
                        metadata,
                        '{http://id.loc.gov/ontologies/bibframe/}ISBN'
                    ).text = sf

        # bf:ISSN
        for n in ('022'):
            for f in self.digital_record.get_fields(n):
                for sf in f.get_subfields(*list(string.ascii_lowercase)):
                    ElementTree.SubElement(
                        metadata,
                        '{http://id.loc.gov/ontologies/bibframe/}ISSN'
                    ).text = sf

        # dcterms:isPartOf
        for f in self.digital_record.get_fields('700'):
            if f['t'] is not None:
                for sf in f.get_subfields('a'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/terms/}isPartOf'
                    ).text = sf

        for f in self.digital_record.get_fields('830'):
            for sf in f.get_subfields(*list(string.ascii_lowercase)):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}isPartOf'
                ).text = sf

        # dcterms:issued
        issued = set()
        for f in self.digital_record.get_fields('260'):
            for sf in f.get_subfields('c'):
                issued.add(process_date_string(sf))
        for f in self.digital_record.get_fields('264'):
            if f.indicator2 == '1':
                for sf in f.get_subfields('c'):
                    issued.add(process_date_string(sf))
        if issued:
            for i in sorted(list(issued)):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}issued'
                ).text = i

        # dc:language
        # get language from specific character positions in the 008. 
        # see https://www.loc.gov/marc/languages/ for a lookup table. 
        marc_code_list_for_languages = {
            'eng': 'English'
        }

        for f in self.digital_record.get_fields('008'):
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}language'
            ).text = marc_code_list_for_languages[f.value()[35:38]]

        # dc:medium
        for f in self.digital_record.get_fields('338'):
            sf = f.get_subfields(*list(string.ascii_lowercase))
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/elements/1.1/}medium'
                ).text = ' '.join(sf)

        # bf:place
        places = set()
        for f in self.digital_record.get_fields('260'):
            for sf in f.get_subfields('a'):
                places.add(remove_marc_punctuation(sf))

        for f in self.digital_record.get_fields('264'):
            if f.indicator2 == '1':
                for sf in f.get_subfields('a'):
                    places.add(remove_marc_punctuation(sf))

        for p in sorted(list(places)):
            ElementTree.SubElement(
                metadata,
                '{http://id.loc.gov/ontologies/bibframe/}place'
            ).text = p

        # dc:publisher
        for f in self.digital_record.get_fields('260'):
            for sf in f.get_subfields('b'):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/elements/1.1/}publisher'
                ).text = remove_marc_punctuation(sf)

        for f in self.digital_record.get_fields('264'):
            if f.indicator2 == '1':
                for sf in f.get_subfields('b'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}publisher'
                    ).text = remove_marc_punctuation(sf)

        # dc:relation
        for f in self.digital_record.get_fields('730'):
            for sf in f.get_subfields('a'):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/elements/1.1/}relation'
                ).text = sf

        # dcterms:spatial
        spatials = []
        for f in self.digital_record.get_fields('651'):
            spatial = []
            if f.indicator2 == '7' and f['2'] == 'fast':
                for sf in f.get_subfields('a', 'z'):
                    spatial.append(remove_marc_punctuation(sf))
            spatials.append(spatial)

        spatials = remove_subsets(spatials)

        for s in spatials:
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/terms/}spatial'
            ).text = ' -- '.join(s)

        # dc:subject
        subjects = set()
        for f in self.digital_record.get_fields('650'):
            for sf in f.get_subfields('a', 'x'):
                subjects.add(remove_marc_punctuation(sf))

        for s in sorted(list(subjects)):
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}subject'
            ).text = s

        # dcterms:temporal
        for f in self.digital_record.get_fields('650'):
            for sf in f.get_subfields('y'):
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/terms/}temporal'
                ).text = sf

        # dc:title
        for f in self.digital_record.get_fields('245'):
            title = []
            for sf in f.get_subfields('a', 'b'):
                title.append(sf)
            if title:
                ElementTree.SubElement(
                    metadata,
                    '{http://purl.org/dc/elements/1.1/}title'
                ).text = ' '.join(title)

        # mods:titleUniform
        for n in ('130', '240'):
            for f in self.digital_record.get_fields(n):
                sf = f.get_subfields(*list(string.ascii_lowercase))
                if sf:
                    ElementTree.SubElement(
                        metadata,
                        '{http://www.loc.gov/mods/v3/}titleUniform'
                    ).text = ' '.join(sf)

        # dc:type
        types = set()
        for f in self.digital_record.get_fields('336'):
            for sf in f.get_subfields('a'):
                types.add(remove_marc_punctuation(sf))

        for n in ('650', '651'):
            for f in self.digital_record.get_fields(n): 
                for sf in f.get_subfields('v'):
                    types.add(remove_marc_punctuation(sf))

        for f in self.digital_record.get_fields('655'):
            if f['2'] == 'fast':
                for sf in f.get_subfields(*list(string.ascii_lowercase)):
                    types.add(remove_marc_punctuation(sf))

        for t in sorted(list(types)):
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}type'
            ).text = t

        return metadata
            
    def __str__(self):
        return ElementTree.tostring(self._asxml(), 'utf-8', method='xml').decode('utf-8')


class DigitalMediaArchiveFilemakerToDc:
    def _asxml(self):
        metadata = ElementTree.Element('metadata')


class SocSciMapsMarcXmlToDc(MarcXmlToDc):
    def _asxml(self):
        metadata = super()._asxml()

        # remove dc:coverage
        for c in metadata.findall('{http://purl.org/dc/elements/1.1/}coverage'):
            metadata.remove(c)

        # remove dc:medium
        for s in metadata.findall('{http://purl.org/dc/elements/1.1/}medium'):
            metadata.remove(s)

        # remove existing dc:type elements, then add only the ones we
        # want back.
        for t in metadata.findall('{http://purl.org/dc/elements/1.1/}type'):
            metadata.remove(t)

        types = set()
        for n in ('650', '651'):
            for f in self.digital_record.get_fields(n):
                for sf in f.get_subfields('v'):
                    types.add(remove_marc_punctuation(sf))

        for f in self.digital_record.get_fields('655'):
            if f['2'] == 'fast':
                for sf in f.get_subfields(*list(string.ascii_lowercase)):
                    types.add(remove_marc_punctuation(sf))

        for t in sorted(list(types)):
            ElementTree.SubElement(
                metadata,
                '{http://purl.org/dc/elements/1.1/}type'
            ).text = t

        return metadata


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
    BF = Namespace('http://id.loc.gov/ontologies/bibframe/')
    EDM = Namespace('http://www.europeana.eu/schemas/edm/')
    ERC = Namespace('http://purl.org/kernel/elements/1.1/')
    MIX = Namespace('http://www.loc.gov/mix/v20/')
    OAI = Namespace('http://www.openarchives.org/OAI/2.0/')
    ORE = Namespace('http://www.openarchives.org/ore/terms/')
    PREMIS = Namespace('info:lc/xmlns/premis-v2/')
    VRA = Namespace('http://purl.org/vra/')

    #REPOSITORY_AGG = URIRef('aggregation/repository.lib.uchicago.edu')
    REPOSITORY_AGG = URIRef('https://repository.lib.uchicago.edu/aggregation')
    REPOSITORY_CHO = URIRef('https://repository.lib.uchicago.edu')
    REPOSITORY_PRO = URIRef('https://repository.lib.uchicago.edu/index.dc.xml')
    #REPOSITORY_REM = URIRef('rem/repository.lib.uchicago.edu')
    REPOSITORY_REM = URIRef('https://repository.lib.uchicago.edu/rem')

    #DIGCOL_AGG = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections')
    DIGCOL_AGG = URIRef('https://repository.lib.uchicago.edu/digitalcollections/Aggregation')
    DIGCOL_CHO = URIRef('https://repository.lib.uchicago.edu/digitalcollections')
    DIGCOL_PRO = URIRef('https://repository.lib.uchicago.edu/digitalcollections/index.dc.xml')
    #DIGCOL_REM = URIRef('rem/repository.lib.uchicago.edu/digitalcollections')
    DIGCOL_REM = URIRef('https://repository.lib.uchicago.edu/digitalcollections/rem')

    #MAPCOL_AGG = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections/maps')
    MAPCOL_AGG = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/aggregation')
    MAPCOL_CHO = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')
    MAPCOL_PRO = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/index.dc.xml')
    #MAPCOL_REM = URIRef('rem/repository.lib.uchicago.edu/digitalcollections/maps')
    MAPCOL_REM = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/rem')

    #SSMAPS_AGG = URIRef('aggregation/repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
    SSMAPS_AGG = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/aggregation')
    SSMAPS_CHO = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
    SSMAPS_PRO = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/index.dc.xml')
    #SSMAPS_REM = URIRef('rem/repository.lib.uchicago.edu/digitalcollections/maps/chisoc')
    SSMAPS_REM = URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc/rem')

    graph = Graph()
    for prefix, ns in (('bf', BF), ('dc', DC), ('dcterms', DCTERMS),
                       ('edm', EDM), ('erc', ERC), ('mix', MIX), 
                       ('ore', ORE), ('premis', PREMIS)):
        graph.bind(prefix, ns)

    def __init__(self, digital_record, print_record, master_file_metadata):
        """Initialize an instance of the class MarcXmlToEDM.

        Args:
            graph (Graph): a EDM graph collection from a single record.
        """
        self.digital_record = digital_record
        self.print_record = print_record
        self.dc = SocSciMapsMarcXmlToDc(digital_record, print_record)
        self.master_file_metadata = master_file_metadata

        if isinstance(self.dc.identifier, list):
            self.identifier = self.dc.identifier[0]
        else:
            self.identifier = self.dc.identifier

        self.short_id = self.identifier.replace('http://pi.lib.uchicago.edu/1001', '')

        self.agg = URIRef('/aggregation/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.cho = URIRef('/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.pro = URIRef('/digital_collections/IIIF_Files/social_scientists_maps/{0}/{0}.dc.xml'.format(self.identifier.split('/').pop()))
        self.rem = URIRef('/rem/digital_collections/IIIF_Files{}'.format(self.short_id))
        self.wbr = URIRef('/digital_collections/IIIF_Files{}.tif'.format(self.short_id))

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
        self.graph.add((self.agg, RDF.type,                self.ORE.Aggregation))
        self.graph.add((self.agg, DCTERMS.created,         self.now))
        self.graph.add((self.agg, DCTERMS.modified,        self.now))
        self.graph.add((self.agg, self.EDM.aggregatedCHO,  self.cho))
        self.graph.add((self.agg, self.EDM.dataProvider,   Literal("The University of Chicago Library")))
        self.graph.add((self.agg, self.ORE.isDescribedBy,  self.rem))
        self.graph.add((self.agg, self.EDM.isShownAt,      Literal(self.identifier)))
        self.graph.add((self.agg, self.EDM.isShownBy,      self.wbr))
        self.graph.add((self.agg, self.EDM.object,         self.wbr))
        self.graph.add((self.agg, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((self.agg, self.EDM.rights,         URIRef('https://rightsstatements.org/page/InC/1.0/?language=en')))

        self._build_cho()

        # proxy for the item.
        self.graph.add((self.pro,      RDF.type,           self.ORE.Proxy))
        self.graph.add((self.pro,      URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.pro,      self.ORE.proxyFor,  self.cho))
        self.graph.add((self.pro,      self.ORE.proxyIn,   self.agg))

        # resource map for the item.
        self.graph.add((self.rem,      DCTERMS.created,    self.now))
        self.graph.add((self.rem,      DCTERMS.modified,   self.now))
        self.graph.add((self.rem,      DCTERMS.creator,    URIRef('http://library.uchicago.edu')))
        self.graph.add((self.rem,      RDF.type,           self.ORE.ResourceMap))
        self.graph.add((self.rem,      self.ORE.describes, self.agg))

        self._build_web_resources()

        # connect the item to its collection.
        self.graph.add((URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc'), DCTERMS.hasPart, self.cho))

    def _build_cho(self):
        """The cultural herigate object is the map itself. 

        This method adds triples that describe the cultural heritage object.

        Args:
            agg (URIRef): aggregation 
            cho (URIRef): cultural heritage object

        Side Effect:
            Add triples to self.graph
        """

        self.graph.add((self.cho, RDF.type, self.EDM.ProvidedCHO))
        for pre, obj_str in (
            (self.BF.ClassificationLcc, '{http://id.loc.gov/ontologies/bibframe/}ClassificationLcc'),
            (DC.coverage,               '{http://purl.org/dc/elements/1.1/}coverage'),
            (DC.creator,                '{http://purl.org/dc/elements/1.1/}creator'),
            (DC.description,            '{http://purl.org/dc/elements/1.1/}description'),
            (DC.extent,                 '{http://purl.org/dc/elements/1.1/}extent'),
            (DCTERMS.hasFormat,         '{http://purl.org/dc/terms/}hasFormat'),
            (DC.identifier,             '{http://purl.org/dc/elements/1.1/}identifier'),
            (DC.language,               '{http://purl.org/dc/elements/1.1/}language'),
            (self.BF.Local,             '{http://id.loc.gov/ontologies/bibframe/}Local'),
            (DC.publisher,              '{http://purl.org/dc/elements/1.1/}publisher'),
            (DC.rights,                 '{http://purl.org/dc/elements/1.1/}rights'),
            (DCTERMS.spatial,           '{http://purl.org/dc/terms/}spatial'),
            (DC.subject,                '{http://purl.org/dc/elements/1.1/}subject'),
            (DC.title,                  '{http://purl.org/dc/elements/1.1/}title'),
            (DC.type,                   '{http://purl.org/dc/elements/1.1/}type'),
            (self.ERC.what,             '{http://purl.org/dc/elements/1.1/}title'),
            (self.ERC.who,              '{http://purl.org/dc/elements/1.1/}creator')
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
            self.graph.add((self.cho, self.EDM.year, Literal(process_date_string(d[0]))))
            self.graph.add((self.cho, self.ERC.when, Literal(process_date_string(d[0]))))

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

        self.graph.add((self.cho, DCTERMS.isPartOf, URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((self.cho, self.EDM.currentLocation, Literal('Map Collection Reading Room (Room 370)')))
        self.graph.add((self.cho, self.EDM.type, Literal('IMAGE')))
        self.graph.add((self.cho, self.ERC.where, self.cho))

    def _build_web_resources(self):
        for metadata in self.master_file_metadata:
            self.graph.add((self.wbr, RDF.type, self.EDM.WebResource))
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
                ('info:lc/xmlns/premis-v2/eventDateTime',             self.now),
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
                self.graph.add((self.wbr, URIRef(p), Literal(o)))

    @classmethod
    def build_repository_triples(self):
        """Add triples for the repository itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation for the repository
        self.graph.add((self.REPOSITORY_AGG, RDF.type,               self.ORE.Aggregation))
        self.graph.add((self.REPOSITORY_AGG, DCTERMS.created,        now))
        self.graph.add((self.REPOSITORY_AGG, DCTERMS.modified,       now))
        self.graph.add((self.REPOSITORY_AGG, self.EDM.aggregatedCHO, self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_AGG, self.EDM.dataProvider,  Literal("The University of Chicago Library")))
        self.graph.add((self.REPOSITORY_AGG, self.EDM.isShownAt,     URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.REPOSITORY_AGG, self.EDM.provider,      Literal("The University of Chicago Library")))
        self.graph.add((self.REPOSITORY_AGG, self.EDM.rights,        URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.REPOSITORY_AGG, self.ORE.isDescribedBy, self.REPOSITORY_REM))

        # cultural heritage object for the repository
        self.graph.add((self.REPOSITORY_CHO, RDF.type,               self.EDM.ProvidedCHO))
        self.graph.add((self.REPOSITORY_CHO, DC.coverage,            URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((self.REPOSITORY_CHO, DC.coverage,            Literal('World')))
        self.graph.add((self.REPOSITORY_CHO, DC.creator,             Literal('The University of Chicago Library')))
        self.graph.add((self.REPOSITORY_CHO, DC.date,                Literal('2006')))
        self.graph.add((self.REPOSITORY_CHO, DC.description,         Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.REPOSITORY_CHO, DC.identifier,          URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.REPOSITORY_CHO, DC.rights,              URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.REPOSITORY_CHO, DC.title,               Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.REPOSITORY_CHO, DC.type,                Literal('Collection')))
        self.graph.add((self.REPOSITORY_CHO, DCTERMS.hasPart,        URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((self.REPOSITORY_CHO, DCTERMS.hasPart,        URIRef('https://repository.lib.uchicago.edu/specialcollections')))
        self.graph.add((self.REPOSITORY_CHO, self.EDM.type,          Literal('COLLECTION')))
        self.graph.add((self.REPOSITORY_CHO, self.EDM.year,          Literal('2006'))) 
        self.graph.add((self.REPOSITORY_CHO, self.ERC.what,          Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.REPOSITORY_CHO, self.ERC.when,          Literal('2006')))
        self.graph.add((self.REPOSITORY_CHO, self.ERC.where,         self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_CHO, self.ERC.who,           Literal('The University of Chicago Library')))

        # proxy for the repository
        self.graph.add((self.REPOSITORY_PRO, RDF.type,               self.ORE.Proxy))
        self.graph.add((self.REPOSITORY_PRO, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.REPOSITORY_PRO, self.ORE.proxyFor,      self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_PRO, self.ORE.proxyIn,       self.REPOSITORY_AGG))

        # resource map for the repository
        self.graph.add((self.REPOSITORY_REM, RDF.type,               self.ORE.ResourceMap))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.created,        now))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.modified,       now))
        self.graph.add((self.REPOSITORY_REM, DCTERMS.creator,        self.REPOSITORY_CHO))
        self.graph.add((self.REPOSITORY_REM, self.ORE.describes,     self.REPOSITORY_AGG))
 
    @classmethod
    def build_digital_collections_triples(self):
        """Add triples for digital collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation for digital collections
        self.graph.add((self.DIGCOL_AGG, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((self.DIGCOL_AGG, DCTERMS.created,         now))
        self.graph.add((self.DIGCOL_AGG, DCTERMS.modified,        now))
        self.graph.add((self.DIGCOL_AGG, self.EDM.aggregatedCHO,  URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.DIGCOL_AGG, self.EDM.dataProvider,   Literal('The University of Chicago Library')))
        self.graph.add((self.DIGCOL_AGG, self.EDM.isShownAt,      URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((self.DIGCOL_AGG, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((self.DIGCOL_AGG, self.EDM.rights,         URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.DIGCOL_AGG, self.ORE.isDescribedBy,  self.DIGCOL_REM))

        # cultural heritage object for digital collections
        self.graph.add((self.DIGCOL_CHO, RDF.type,                self.EDM.ProvidedCHO))
        self.graph.add((self.DIGCOL_CHO, DC.coverage,             URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((self.DIGCOL_CHO, DC.coverage,             Literal('World')))
        self.graph.add((self.DIGCOL_CHO, DC.creator,              Literal('The University of Chicago Library')))
        self.graph.add((self.DIGCOL_CHO, DC.date,                 Literal('2006')))
        self.graph.add((self.DIGCOL_CHO, DC.description,          Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((self.DIGCOL_CHO, DC.identifier,           URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.DIGCOL_CHO, DC.rights,               URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.DIGCOL_CHO, DC.title,                Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((self.DIGCOL_CHO, DC.type,                 Literal('Collection')))
        self.graph.add((self.DIGCOL_CHO, DCTERMS.hasPart,         URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((self.DIGCOL_CHO, DCTERMS.isPartOf,        URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.DIGCOL_CHO, self.EDM.type,           Literal('COLLECTION')))
        self.graph.add((self.DIGCOL_CHO, self.EDM.year,           Literal('2014')))
        self.graph.add((self.DIGCOL_CHO, self.ERC.what,           Literal('The University of Chicago Library Digital Collections')))
        self.graph.add((self.DIGCOL_CHO, self.ERC.when,           Literal('2014')))
        self.graph.add((self.DIGCOL_CHO, self.ERC.where,          URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((self.DIGCOL_CHO, self.ERC.who,            Literal('The University of Chicago Library')))

        # proxy for digital collections
        self.graph.add((self.DIGCOL_PRO, RDF.type,                self.ORE.Proxy))
        self.graph.add((self.DIGCOL_PRO, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.DIGCOL_PRO, self.ORE.proxyFor,       self.DIGCOL_CHO))
        self.graph.add((self.DIGCOL_PRO, self.ORE.proxyIn,        self.DIGCOL_AGG))

        # resource map for digital collections.
        self.graph.add((self.DIGCOL_REM, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((self.DIGCOL_REM, DCTERMS.created,         now))
        self.graph.add((self.DIGCOL_REM, DCTERMS.modified,        now))
        self.graph.add((self.DIGCOL_REM, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.DIGCOL_REM, self.ORE.describes,      self.DIGCOL_AGG))

    @classmethod
    def build_map_collection_triples(self):
        """Add triples for the map collections itself, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation for the map collection
        self.graph.add((self.MAPCOL_AGG, RDF.type,                self.ORE.Aggregation))
        self.graph.add((self.MAPCOL_AGG, DCTERMS.created,         now))
        self.graph.add((self.MAPCOL_AGG, DCTERMS.modified,        now))
        self.graph.add((self.MAPCOL_AGG, self.EDM.aggregatedCHO,  URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.MAPCOL_AGG, self.EDM.dataProvider,   Literal('The University of Chicago Library')))
        self.graph.add((self.MAPCOL_AGG, self.EDM.isShownAt,      self.MAPCOL_CHO))
        self.graph.add((self.MAPCOL_AGG, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((self.MAPCOL_AGG, self.EDM.rights,         URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.MAPCOL_AGG, self.ORE.isDescribedBy,  self.MAPCOL_REM))

        # cultural heritage object for the map collection
        self.graph.add((self.MAPCOL_CHO, RDF.type,                self.EDM.ProvidedCHO))
        self.graph.add((self.MAPCOL_CHO, DC.coverage,             URIRef('https://vocab.getty.edu/page/tgn/7029392')))
        self.graph.add((self.MAPCOL_CHO, DC.coverage,             Literal('World')))
        self.graph.add((self.MAPCOL_CHO, DC.creator,              Literal('The University of Chicago Library')))
        self.graph.add((self.MAPCOL_CHO, DC.date,                 Literal('2006')))
        self.graph.add((self.MAPCOL_CHO, DC.description,          Literal('The University of Chicago Library Map Collection')))
        self.graph.add((self.MAPCOL_CHO, DC.identifier,           URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.MAPCOL_CHO, DC.rights,               URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.MAPCOL_CHO, DC.title,                Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.MAPCOL_CHO, DC.type,                 Literal('Collection')))
        self.graph.add((self.MAPCOL_CHO, DCTERMS.hasPart,         URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((self.MAPCOL_CHO, DCTERMS.isPartOf,        URIRef('https://repository.lib.uchicago.edu/digitalcollections')))
        self.graph.add((self.MAPCOL_CHO, self.EDM.type,           Literal('COLLECTION')))
        self.graph.add((self.MAPCOL_CHO, self.EDM.year,           Literal('2014')))
        self.graph.add((self.MAPCOL_CHO, self.ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.MAPCOL_CHO, self.ERC.when,           Literal('2014')))
        self.graph.add((self.MAPCOL_CHO, self.ERC.where,          URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((self.MAPCOL_CHO, self.ERC.who,            Literal('The University of Chicago Library')))

        # proxy for the map collection
        self.graph.add((self.MAPCOL_PRO, RDF.type,                self.ORE.Proxy))
        self.graph.add((self.MAPCOL_PRO, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.MAPCOL_PRO, self.ORE.proxyFor,       self.MAPCOL_CHO))
        self.graph.add((self.MAPCOL_PRO, self.ORE.proxyIn,        self.MAPCOL_AGG))

        # resource map for the map collection 
        self.graph.add((self.MAPCOL_REM, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((self.MAPCOL_REM, DCTERMS.created,         now))
        self.graph.add((self.MAPCOL_REM, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.MAPCOL_REM, DCTERMS.modified,        now))
        self.graph.add((self.MAPCOL_REM, self.ORE.describes,      self.MAPCOL_AGG))

    @classmethod
    def build_socscimap_collection_triples(self):
        """Add triples for the social scientist map collection, and to connect items with each other. 

        Side Effect:
            Add triples to self.graph
        """
 
        now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

        # aggregation for the social scientist maps collection
        self.graph.add((self.SSMAPS_AGG, RDF.type,                self.ORE.Aggregation))
        self.graph.add((self.SSMAPS_AGG, DCTERMS.created,         now))
        self.graph.add((self.SSMAPS_AGG, DCTERMS.modified,        now))
        self.graph.add((self.SSMAPS_AGG, self.EDM.aggregatedCHO,  URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.SSMAPS_AGG, self.EDM.dataProvider,   Literal('The University of Chicago Library')))
        self.graph.add((self.SSMAPS_AGG, self.EDM.isShownAt,      self.SSMAPS_CHO))
        self.graph.add((self.SSMAPS_AGG, self.EDM.provider,       Literal('The University of Chicago Library')))
        self.graph.add((self.SSMAPS_AGG, self.EDM.rights,         URIRef('https://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.SSMAPS_AGG, self.ORE.isDescribedBy,  self.SSMAPS_REM))

        # cultural heritage object for the social scientist maps collection
        self.graph.add((self.SSMAPS_CHO, RDF.type,                self.EDM.ProvidedCHO))
        self.graph.add((self.SSMAPS_CHO, DC.coverage,             URIRef('https://vocab.getty.edu/page/tgn/7013596')))
        self.graph.add((self.SSMAPS_CHO, DC.coverage,             Literal('Chicago')))
        self.graph.add((self.SSMAPS_CHO, DC.creator,              Literal('The University of Chicago Library')))
        self.graph.add((self.SSMAPS_CHO, DC.date,                 Literal('2006')))
        self.graph.add((self.SSMAPS_CHO, DC.description,          Literal('The University of Chicago Library Social Scientists Map Collection')))
        self.graph.add((self.SSMAPS_CHO, DC.identifier,           URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.SSMAPS_CHO, DC.rights,               URIRef('http://creativecommons.org/licenses/by-nc/4.0/')))
        self.graph.add((self.SSMAPS_CHO, DC.title,                Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.SSMAPS_CHO, DC.type,                 Literal('Collection')))
        self.graph.add((self.SSMAPS_CHO, DCTERMS.isPartOf,        URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps')))
        self.graph.add((self.SSMAPS_CHO, self.EDM.type,           Literal('COLLECTION')))
        self.graph.add((self.SSMAPS_CHO, self.EDM.year,           Literal('2014')))
        self.graph.add((self.SSMAPS_CHO, self.ERC.what,           Literal('The University of Chicago Library Digital Repository')))
        self.graph.add((self.SSMAPS_CHO, self.ERC.when,           Literal('2014')))
        self.graph.add((self.SSMAPS_CHO, self.ERC.where,          URIRef('https://repository.lib.uchicago.edu/digitalcollections/maps/chisoc')))
        self.graph.add((self.SSMAPS_CHO, self.ERC.who,            Literal('The University of Chicago Library')))

        # proxy for the social scientists maps collection
        self.graph.add((self.SSMAPS_PRO, RDF.type,                self.ORE.Proxy))
        self.graph.add((self.SSMAPS_PRO, URIRef('http://purl.org/dc/elements/1.1/format'), Literal('application/xml')))
        self.graph.add((self.SSMAPS_PRO, self.ORE.proxyFor,       self.SSMAPS_CHO))
        self.graph.add((self.SSMAPS_PRO, self.ORE.proxyIn,        self.SSMAPS_AGG))

        # resource map for the social scientists map collection
        self.graph.add((self.SSMAPS_REM, RDF.type,                self.ORE.ResourceMap))
        self.graph.add((self.SSMAPS_REM, DCTERMS.created,         now))
        self.graph.add((self.SSMAPS_REM, DCTERMS.creator,         URIRef('https://repository.lib.uchicago.edu')))
        self.graph.add((self.SSMAPS_REM, self.ORE.describes,      self.SSMAPS_AGG))

    @classmethod
    def triples(self):
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
