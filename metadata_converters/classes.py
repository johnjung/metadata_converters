import datetime, getpass, hashlib, jinja2, json, magic, os, \
       pymarc, random, re, string, sys
import xml.etree.ElementTree as ElementTree

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, DC, DCTERMS, XSD
from rdflib.plugins.sparql import prepareQuery


ARK = Namespace('ark:/61001/')
BF = Namespace('http://id.loc.gov/ontologies/bibframe/')
EDM = Namespace('http://www.europeana.eu/schemas/edm/')
ERC = Namespace('https://www.dublincore.org/groups/kernel/spec/')
MADSRDF = Namespace('http://www.loc.gov/mads/rdf/v1#')
MIX = Namespace('http://www.loc.gov/mix/v20/')
OAI = Namespace('http://www.openarchives.org/OAI/2.0/')
ORE = Namespace('http://www.openarchives.org/ore/terms/')
PREMIS = Namespace('info:lc/xmlns/premis-v2/')
PREMIS2 = Namespace('http://www.loc.gov/premis/rdf/v1#')
PREMIS3 = Namespace('http://www.loc.gov/premis/rdf/v3/')
VRA = Namespace('http://purl.org/vra/')


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

class NoidManager():
    """A class to manage NOIDS for digital collections."""
    def __init__(self, pair_tree_root):
        self.pair_tree_root = pair_tree_root
        self.extended_digits = '0123456789bcdfghjkmnpqrstvwxz'

    def list(self):
        """Get a list of the NOIDs present."""
    
        identifiers = []
        for root, dirs, files in os.walk(self.pair_tree_root):
            for file in files:
                if file in ('0=ocfl_object_1.0',):
                    identifiers.append(root[len(self.pair_tree_root):].replace(os.sep, ''))
        return identifiers

    def generate_check_digit(self, noid):
        """Multiply each characters ordinal value by it's position, starting at
           position 1. Sum the products. Then do modulo 29 to get the check digit
           in extended characters."""
        s = 0
        p = 1
        for c in noid:
            if self.extended_digits.find(c) > -1:
                s += (self.extended_digits.find(c) * p)
            p += 1
        return self.extended_digits[s % len(self.extended_digits)]

    def test_noid_check_digit(self, noid):
        """Use this for NOIDs that came from other sources."""
        return self.generate_check_digit(self.extended_digits, noid[:-1]) == noid[-1:]

    def create(self):
        """create a UChicago NOID in the form 'b2.reedeedeedk', where: 
         
           e is an extended digit, 
           d is a digit, 
           and k is a check digit.
    
           Note that all UChicago Library NOIDs start with the prefix "b2", so
           that's hardcoded into this function."""
    
        noid = [
            'b',
            '2',
            random.choice(self.extended_digits),
            random.choice(self.extended_digits),
            random.choice(self.extended_digits[:10]),
            random.choice(self.extended_digits),
            random.choice(self.extended_digits),
            random.choice(self.extended_digits[:10]),
            random.choice(self.extended_digits),
            random.choice(self.extended_digits),
            random.choice(self.extended_digits[:10])
        ]
        noid.append(self.generate_check_digit(''.join(noid)))
        return ''.join(noid)

    def path(self, noid):
        """split the noid into two character directories."""
        return os.sep.join([noid[i] + noid[i+1] for i in range(0, len(noid), 2)])

    def noid_is_unique(self, noid, path):
        """Check to see if ARKS with that noid exist in our system. 
           Returns true if the NOID is unique in our system. 
           (Note that with 600B possible NOIDs, it is very unlikely that this
           function will ever return False.)"""
        return noid not in self.list(path)


class DigitalCollectionToEDM:
    MAPS = Namespace('https://repository.lib.uchicago.edu/digital_collections/maps')
    MAPS_AGG = MAPS['/aggregation']
    MAPS_CHO = MAPS['']
    MAPS_REM = MAPS['/rem']

    CHISOC = Namespace('https://repository.lib.uchicago.edu/digital_collections/maps/chisoc')
    CHISOC_AGG = CHISOC['/aggregation']
    CHISOC_CHO = CHISOC['']
    CHISOC_REM = CHISOC['/rem']

    graph = Graph()
    for prefix, ns in (('bf', BF), ('dc', DC), ('dcterms', DCTERMS),
                       ('edm', EDM), ('erc', ERC), ('madsrdf', MADSRDF),
                       ('mix', MIX), ('ore', ORE), ('premis', PREMIS),
                       ('premis2', PREMIS2), ('premis3', PREMIS3)):
        graph.bind(prefix, ns)

    def __init__(self):
        self.graph = Graph()
        for prefix, ns in (('bf', BF), ('dc', DC), ('dcterms', DCTERMS),
                           ('edm', EDM), ('erc', ERC), ('madsrdf', MADSRDF),
                           ('mix', MIX), ('ore', ORE), ('premis', PREMIS),
                           ('premis2', PREMIS2), ('premis3', PREMIS3)):
            self.graph.bind(prefix, ns)

        self.now = Literal(datetime.datetime.utcnow(), datatype=XSD.dateTime)

    def agg_graph(self, agg, cho, rem, wbr):
        for p, o in ((RDF.type,          ORE.Aggregation),
                     (EDM.aggregatedCHO, cho),
                     (EDM.dataProvider,  Literal("University of Chicago Library")),
                     (ORE.isDescribedBy, rem),
                     (EDM.isShownAt,     wbr),
                     (EDM.isShownBy,     wbr),
                     (EDM.object,        URIRef('http://example.org/')),
                     (EDM.provider,      Literal('University of Chicago Library')),
                     (EDM.rights,        URIRef('http://creativecommons.org/licenses/by-nc/4.0/'))):
            self.graph.add((agg, p, o))
   
    def rem_graph(self, agg, rem, now):
        # as per CB on 11/6/2020, DCTERMS:creator should be
        # https://repository.lib.uchicago.edu/ - note https and trailing
        # slash, while ProvidedCHOs should not include a trailing slash.
        for p, o in ((RDF.type,         ORE.ResourceMap),
                     (DCTERMS.modified, now),
                     (DCTERMS.creator,  URIRef('https://repository.lib.uchicago.edu/')),
                     (ORE.describes,    agg)):
            self.graph.add((rem, p, o))

    @classmethod
    def triples(self):
        """Return EDM data as a string.

        Returns:
            str
        """
        return self.graph.serialize(format='turtle', base='ark:/61001/').decode("utf-8")


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
    def __init__(self, digital_record, print_record, noid):
        """
            digital_record_id: identifier for the digital record.
        """
        self.digital_record = digital_record
        self.print_record = print_record
        self.noid = noid

        ElementTree.register_namespace(
            'bf', 'http://id.loc.gov/ontologies/bibframe/')
        ElementTree.register_namespace(
            'dc', 'http://purl.org/dc/elements/1.1/')
        ElementTree.register_namespace(
            'dcterms', 'http://purl.org/dc/terms/')
        ElementTree.register_namespace(
            'madsrdf', 'http://www.loc.gov/mads/rdf/v1#')
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

        # madsrdf:ConferenceName
        for f in self.digital_record.get_fields('111'):
            sf = f.get_subfields(*list(string.ascii_lowercase))
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://www.loc.gov/mads/rdf/v1#}ConferenceName'
                ).text = ' '.join(sf)

        # madsrdf:CorporateName
        for f in self.digital_record.get_fields('110'):
            sf = f.get_subfields(*list(string.ascii_lowercase))
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://www.loc.gov/mads/rdf/v1#}CorporateName'
                ).text = ' '.join(sf)

        for f in self.digital_record.get_fields('710'):
            for sf in f.get_subfields('a'):
                ElementTree.SubElement(
                    metadata,
                    '{http://www.loc.gov/mads/rdf/v1#}CorporateName'
                ).text = remove_marc_punctuation(sf)

        # dc:coverage
        for f in self.digital_record.get_fields('651'):
            if f.indicator2 == '7' and f['2'] == 'fast':
                for sf in f.get_subfields('a'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://purl.org/dc/elements/1.1/}coverage'
                    ).text = remove_marc_punctuation(sf)

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
            for sf in f.get_subfields('b'):
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

        # dc:identifier
        ElementTree.SubElement(
            metadata,
            '{http://purl.org/dc/elements/1.1/}identifier'
        ).text = 'ark:/61001/{}'.format(self.noid)

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
            'eng': 'en'
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

        # madsrdf:PersonalName
        for f in self.digital_record.get_fields('100'):
            sf = f.get_subfields('a')
            if sf:
                ElementTree.SubElement(
                    metadata,
                    '{http://www.loc.gov/mads/rdf/v1#}PersonalName'
                ).text = ' '.join(sf)

        for f in self.digital_record.get_fields('700'):
            if f['t'] is None:
                for sf in f.get_subfields('a'):
                    ElementTree.SubElement(
                        metadata,
                        '{http://www.loc.gov/mads/rdf/v1#}PersonalName'
                    ).text = remove_marc_punctuation(sf)

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

        # bf:scale
        for f in self.digital_record.get_fields('255'):
            for sf in f.get_subfields('a'):
                ElementTree.SubElement(
                    metadata,
                    '{http://id.loc.gov/ontologies/bibframe/}scale'
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
