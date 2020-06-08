# -*- coding: utf-8 -*-
import json, pymarc, sys, unittest
from metadata_converters import MarcXmlConverter, SocSciMapsMarcXmlToDc, MarcXmlToSchemaDotOrg
from pathlib import Path
from pymarc import MARCReader
import xml.etree.ElementTree as ElementTree

'''
class TestMarcXmlConverter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        """Create test objects. Test data should be placed in the test_data
        directory of this project. It should include sample data from different
        digital collections projects, and the data should be varied enough to 
        be able to catch different kinds of edge cases in testing."""
        super().__init__(*args, **kwargs)
        self.test_init()

    def test_init(self):
        """MarcXmlConverter should have a .record property which is a
        xml.etree.ElementTree.Element."""
        file = Path('test_data/sample_record_01.xml')
        with open(file, 'r', encoding='utf-8') as f:
            data = f.read().replace('\n', '')
            self.assertTrue(len(data) > 0)
        self.collection = MarcXmlConverter(data)
        self.assertIsInstance(self.collection.record, ElementTree.Element)
        self.assertEqual(self.collection.get_marc_field('655', '', '', ''), ['Thematic maps.', 'lcgft'])

    def test_get_marc_field_field_tag(self):
        """Retrieve a marc data field and a control field using the
        get_marc_field() method."""
        self.assertEqual(self.collection.get_marc_field('003', '', '', ''), ['OLE'])
        self.assertEqual(self.collection.get_marc_field('003', '5', '', ''), ['OLE'])
        self.assertEqual(self.collection.get_marc_field('003', '', '5', ''), ['OLE'])
        self.assertEqual(self.collection.get_marc_field('003', '', '', '5'), ['OLE'])
        self.assertEqual(self.collection.get_marc_field('651', '', '', ''),  ['Illinois', 'Chicago.', 'fast', '(OCoLC)fst01204048'])

    def test_get_marc_field_subfield(self):
        """Retrieve a marc data field and subfield using the get_marc_field()
        method."""
        self.assertEqual(self.collection.get_marc_field('650', '[a]', '', '4'), [])
        self.assertEqual(self.collection.get_marc_field('650', '[a]', '4', ''), [])
        self.assertEqual(self.collection.get_marc_field('650', '[a]', '', '')[0], 'Ethnology')

    def test_get_marc_field_indicator_1(self):
        """Retrieve a record with the first indicator marked using the
        get_marc_field() method."""
        self.assertEqual(self.collection.get_marc_field('', '', '2', '4'), [])
        self.assertEqual(self.collection.get_marc_field('', '', '2', ''), [])
        self.assertEqual(self.collection.get_marc_field('650', '[a]', '4', ''), [])
        self.assertEqual(self.collection.get_marc_field('245', '', '1', ''), ['Census tracts of Chicago, 1940', 'Races and nationalities.'])

    def test_get_marc_field_indicator_2(self):
        """Retrieve a record with the second indicator marked using the
        get_marc_field() method."""
        self.assertEqual(self.collection.get_marc_field('', '', '', 's'), [])
        self.assertEqual(self.collection.get_marc_field('655', '[a]', '4', '7'), [])
        self.assertEqual(self.collection.get_marc_field('830', '', '', '0'), ['Social scientists map Chicago.', 'ICU', 'University of Chicago Digital Preservation Collection.', 'ICU'])
'''

class TestSocSciMapsMarcXmlToDc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        """Create test objects. Test data should be placed in the test_data
        directory of this project. It should include sample data from different
        digital collections projects, and the data should be varied enough to 
        be able to catch different kinds of edge cases in testing.

        See:
        https://docs.google.com/spreadsheets/d/1Kz1nfTSBjc2PTJ8hrZ--JCBpKV061sdXQxRxVo8VY_Y/edit#gid=0"""

        super().__init__(*args, **kwargs)
        self.test_init()

    def test_init(self):
        """MarcToDc extends the MarcXmlConverter class and should have a .record property which is a
        xml.etree.ElementTree.Element."""

        digital_records = pymarc.parse_xml_to_array('test_data/ssmaps_digital_record.xml')
        print_records = pymarc.parse_xml_to_array('test_data/ssmaps_print_record.xml')

        self.dc = SocSciMapsMarcXmlToDc(
            digital_records[0],
            print_records[0]
        )

        # read MARC data for testing.
        self.mrc = {}
        for m in ('11435665', '3451312', '5999566', '7368094', '7368097', '7641168'):
            with open('./test_data/{}.mrc'.format(m), 'rb') as fh:
                reader = MARCReader(fh)
                for record in reader:
                    self.mrc[m] = record

        self.ns = {
            'bf': 'http://id.loc.gov/ontologies/bibframe/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

    # def test_alternative_title(self):
    #     """get dcterms:alternative from 246"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_coverage(self):
    #     """get dc:coverage from 651 _7 $a $2 fast"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_date_copyrighted(self):
    #     """get dcterms:dateCopyrighted from 264 _4$c"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_isbn(self):
    #     """get bf:ISBN from the 020"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_issn(self):
    #     """get bf:ISSN from the 022"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_relation(self):
    #     """get dc:relation from 730$a"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_temporal(self):
    #     """get dcterms:temporal from 650 $y"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_title_uniform(self):
    #     """get mods:titleUniform from the 130 and 240."""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    def test_classification_lcc(self):
        """get bf:ClassificationLcc from 929 $a of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('bf:ClassificationLcc', self.ns).text,
            'G4104.C6:2W9 1920z .U5'
        )

    def test_coordinates(self):
        """get bf:coordinates from the 034 $d $e $f $g

           encode this in the following format: 
           $$c(W 87°51'04"-W 87°31'25"/N 42°01'23"-N 41°38'39")

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('bf:coordinates', self.ns).text,
            '''$$c(W 87°37'49"-W 87°34'20"/N 41°47'12"-N 41°45'53")'''
        )

    def test_contributor(self):
        """get dc:contributor from 700 $a (if subfield $t is not present) or 710$a

           use 5999566.mrc (digital) and 7368094.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['5999566'],
                self.mrc['7368094']
            )._asxml().find('dc:contributor', self.ns).text,
            'Behavior Research Fund'
        )

    def test_creator(self):
        """get dc:creator from the 100, 110, and 111

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:creator', self.ns).text,
            'University of Chicago. Department of Sociology'
        )

    def test_description(self):
        """get dc:description from 500, 538

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        test_descriptions = set()

        for d in SocSciMapsMarcXmlToDc(
            self.mrc['7641168'],
            self.mrc['3451312']
        )._asxml().findall('dc:description', self.ns):
            test_descriptions.add(d.text)

        self.assertEqual(
            test_descriptions,
            set((
                'Blue line print.',
                'Shows residential area, vacant area, commercial frontage, railroad property, and transit lines.',
                'Master and use copy. Digital master created according to Benchmark for Faithful Reproductions of Monographs and Serials, Version 1. Digital Library Federation, December 2002. http://www.diglib.org/standards/bmarkfin.htm'
            ))
        )

    def test_format(self):
        """get dc:format from 255 $a $b, 300 $a $c of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        test_formats = set()

        for f in SocSciMapsMarcXmlToDc(
            self.mrc['7641168'],
            self.mrc['3451312']
        )._asxml().findall('dc:format', self.ns):
            test_formats.add(f.text)

        self.assertEqual(
            test_formats,
            set((
                '1 map',
                '45 x 62 cm',
                'Scale [ca. 1:8,000]'
            ))
        )

    def test_has_format(self):
        """get dcterms:hasFormat from 776 $1

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dcterms:hasFormat', self.ns).text,
            'Print version'
        )

    def test_identifier(self):
        """get dc:identifier from 856 $u

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:identifier', self.ns).text,
            'http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-2W9-1920z-U5'
        )

    def test_is_part_of(self):
        """get dcterms:isPartOf from 830

           use 11435665.mrc (digital) and 7368097.mrc (print)"""

        test_is_part_ofs = set()

        for i in SocSciMapsMarcXmlToDc(
            self.mrc['11435665'],
            self.mrc['7368097']
        )._asxml().findall('dcterms:isPartOf', self.ns):
            test_is_part_ofs.add(i.text)

        self.assertEqual(
            test_is_part_ofs,
            set((
                'Social scientists map Chicago.',
                'University of Chicago Digital Preservation Collection.',
                'Social Science Research Committee maps of Chicago.'
            ))
        )

    def test_issued(self):
        """get dcterms:issued from 260$c, 264 _1$c

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dcterms:issued', self.ns).text,
            '1920-1929'
        )

    def test_language(self):
        """get dc:language from the 008

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:language', self.ns).text,
            'English'
        )

    def test_local(self):
        """get bf:Local from 001 of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('bf:Local', self.ns).text,
            'http://pi.lib.uchicago.edu/1001/cat/bib/3451312'
        )

    def test_place(self):
        """get bf:place from 260$a, 264 _1$a

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('bf:place', self.ns).text,
            'Chicago'
        )

    def test_publisher(self):
        """get dc:publisher from 260$b, 264 _1$b

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:publisher', self.ns).text,
            'Dept. of Sociology'
        )

    def test_rights_access(self):
        """get dcterms:accessRights from 506

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dcterms:accessRights', self.ns).text,
            'Digital version available with restrictions Unrestricted online access'
        )

    def test_spatial(self):
        """get dcterms:spatial from 651 _7 $a $z $2 fast

           use 5999566.mrc (digital) and 7368094.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['5999566'],
                self.mrc['7368094']
            )._asxml().find('dcterms:spatial', self.ns).text,
            'Illinois -- Chicago'
        )

    def test_subject(self):
        """get dc:subject from 650 $a, $x

           use 5999566.mrc (digital) and 7368094.mrc (print)"""

        test_subjects = set()

        for f in SocSciMapsMarcXmlToDc(
            self.mrc['5999566'],
            self.mrc['7368094']
        )._asxml().findall('dc:subject', self.ns):
            test_subjects.add(f.text)

        self.assertEqual(
            test_subjects,
            set((
                'Crime',
                'Criminals'
            ))
        )

    def test_title(self):
        """get dc:title from 245 $a $b

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:title', self.ns).text,
            'Woodlawn Community /'
        )

    def test_type(self):
        """get dc:type from 336 $a, 650 $v, 651 $v, 655 $2 fast

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312']
            )._asxml().find('dc:type', self.ns).text,
            'Maps'
        )

class TestSocSciMapsMarcXmlToEDM(unittest.TestCase):
    def test_aggregated_cho(self):
        # edm:aggregatedCHO is a required element.
        # edm:aggregatedCHO <[NOID]/[path/to/providedCHO]>;
        raise NotImplementedError

    def test_classification_lcc(self):
        # bf:ClassificationLcc “[pull from MARC to DC conversion]”
        raise NotImplementedError

    def test_created(self):
        # dcterms:created is machine-generated
        # dcterms:created "[YYYY]-[MM]-[DD]T[HH]:[MM]:[SS]"^^xsd:dateTime;
        edm = SocSciMapsMarcXmlToEDM(
            digital_record,
            print_record,
            [{
                'height': height,
                'md5': md5,
                'mime_type': mime_type,
                'name': '{}.tif'.format(identifier),
                'path': tiff_path,
                'sha256': sha256,
                'size': size,
                'width': width
            }]
        )
        edm.build_item_triples()
        edm.triples()

    def test_creator(self):
        # dc:creator [see MARC to DC converter];
        raise NotImplementedError

    def test_current_location(self): 
        # Use literal string for this collection.
        # edm:currentLocation “Map Collection Reading Room (Room 370)”;
        raise NotImplementedError

    def test_data_provider(self):
        # edm:dataProvider is a constant. It is a required element. According
        # to the EDM Definitions document (v. 5.2.8) “"Although the range of
        # this property is given as edm:Agent, organization names should be
        # provided as an ordinary text string until a Europeana authority file
        # for organizations has been established. At that point providers will
        # be able to send an identifier from the file instead of a text
        # string.” (This applies to edm:provider as well.)
        # edm:dataProvider "University of Chicago Library";
        raise NotImplementedError

    def test_date_copyrighted(self):
        # dcterms:dateCopyrighted [pull from MARC to DC converter];
        raise NotImplementedError

    def test_description(self):
        # If there are multiple 500 fields, concatenate into one dc:description field
        # dc:description [see MARC to DC converter];
        raise NotImplementedError

    def test_format(self):
        # To find the print description fields, consult the record referred to in the 776 $w of the digital 
        # record. This will contain an OCLC number and/or a Bib ID for the equivalent print record.
        # For example,  |w (OCoLC)54383818  |w (ICU)5043398
        # dc:format “[pull from MARC to DC conversion”;
        raise NotImplementedError

    def test_identifier(self):
        # dc:identifier [see MARC to DC converter];
        raise NotImplementedError

    def test_is_described_by(self):
        # ore:isDescribedBy and ore:describes are reciprocal
        # ore:isDescribedBy <[NOID]/rem/[path/to/providedCHO]>;
        # a ore:Aggregation.
        raise NotImplementedError

    def test_is_part_of(self):
        # dcterms:isPartOf [pi for Collection page in Wagtail];
        raise NotImplementedError

    def test_is_shown_at(self):
        # :: see edm:isShownAt
        # <[PI or literal URL for object page]>
        # dc:format "text/html";
        # a edm:WebResource.
        raise NotImplementedError

    def test_is_shown_by(self):
        # :: see edm:isShownBy
        # <[IIIF URL for highest quality image of map]>
        # dc:format "image/tiff";
        # a edm:WebResource.
        raise NotImplementedError

    def test_language(self):
        # For Social Scientists Map Chicago, dc:language is a constant. Otherwise, it might vary.
        # dc:language [see MARC to DC converter];
        raise NotImplementedError

    def test_local(self):
        # bf:Local “[pull from MARC to DC conversion]]”
        raise NotImplementedError

    def test_modified(self):
        # dcterms:modified is machine-generated
        # dcterms:modified "[YYYY]-[MM]-[DD]T[HH]:[MM]:[SS]"^^xsd:dateTime;
        raise NotImplementedError

    def test_object(self):
        # Ask about edm:object. It may vary.
        # edm:object <[IIIF URL for thumbnail equivalent for  map]>;
        raise NotImplementedError

    def test_provider(self):
        # edm:provider is a constant. It is a required element. 
        # edm:provider "University of Chicago Library";
        raise NotImplementedError

    def test_publisher(self):
        # dc:publisher [see MARC to DC converter];
        raise NotImplementedError

    def test_rights(self):
        # edm:rights is probably a constant. It is a required element.
        # edm:rights <https://rightsstatements.org/page/InC/1.0/?language=en>;
        raise NotImplementedError
 
    def test_spatial(self):
        # dcterms:spatial [pull from MARC to DC converter];
        raise NotImplementedError

    def test_subject(self):
        # # For dc:subject use MARCXML 650 fields with second indicator of 7 and subfield $2 
        # # with value “fast”. Eg:
        # # 650	7 |a Ethnology.  |2 fast  |0 http://id.worldcat.org/fast/fst00916106 
        # # Each occurence of 650 should generate a separate dc:subject element.
        # dc:subject [see MARC to DC conversion];
        raise NotImplementedError

    def test_title(self):
        # dc:title [see MARC to DC converter];
        raise NotImplementedError

    def test_type(self):
        # dc:type [see MARC to DC converter];
        # edm:type is UPPER CASE
        # edm:type "IMAGE";
        raise NotImplementedError

    def test_what(self):
        # dc:title -> erc:what
        # erc:what [pull from MARC to DC converter];
        raise NotImplementedError

    def test_when(self):
        # dc:date -> erc:when
        # Erc:when [ copy dcterms:dateCopyrighted ]
        raise NotImplementedError

    def test_where(self):
        # JEJ switched form erc:when [260/264 $c subfield from MARCXML (whichever is populated)];
        # the URI for the edm:ProvidedCHO (i.e., the subject of these assertions) -> erc:where
        # erc:where <[NOID]/[path/to/providedCHO]>;
        raise NotImplementedError

    def test_who(self):
        # dc:creator -> erc:who; if no dc:creator, then ":unav";
        # erc:who [pull from MARC to DC converter];
        raise NotImplementedError

    def test_year(self):
        # Edm: year [ copy dcterms:dateCopyrighted ]
        # JEJ switched the triple above from edm:year [260/264 $c subfield from MARCXML (whichever is populated)];
        raise NotImplementedError


'''
class TestMarcXmlToSchemaDotOrg(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        """Create test objects. Test data should be placed in the test_data
        directory of this project. It should include sample data from different
        digital collections projects, and the data should be varied enough to 
        be able to catch different kinds of edge cases in testing."""
        super().__init__(*args, **kwargs)
        self.test_init()

    def test_init(self):
        """MarcXmlToSchemaDotOrg extends the MarcXmlConverter class and should 
        have a call function that returns data as a dictionary."""
        file = Path('test_data/sample_record_03.xml')
        with open(file, 'r', encoding='utf-8') as f:
            data = f.read().replace('\n', '')
            self.assertTrue(len(data) > 0)
        self.collection = MarcXmlToSchemaDotOrg(data)
        self.collection.schema = self.collection.__call__()
        self.assertIsInstance(self.collection.schema, dict)
        self.assertEqual(self.collection.schema['@context'], 'https://schema.org')
        self.assertEqual(self.collection.schema['@type'], 'Map')
        with self.assertRaises(KeyError):
            self.collection.schema['badKey']

    def test_get_creator(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection._get_creator(), {'@type': 'Person', 'name': 'Mayer, Harold M. (Harold Melvin), 1916-1994.'})

    def test_get_about(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['about'], 'G4104.C6P3 1943 .M21')

    def test_get_alternative_name(self):
        """Be sure the object can return the Schema dictionary. Testing with Lorem Ipsum random value in record"""
        self.assertEqual(self.collection.schema['alternativeName'], 'Duis morbi convallis nullam')

    def test_get_content_location(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['contentLocation'], 'n-us-il 4104 C6 Illinois')

    def test_get_contributor(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['contributor'], 'Thematic')

    def test_get_copyright_year(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['copyrightYear'], '1943.')

    def test_get_date_created(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['dateCreated'], '[2006].')

    def test_get_date_published(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['datePublished'], '1843.')

    def test_get_description(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['description'], '"Figure 2." Also appeared in author\'s Ph. D. dissertation (University of Chicago, 1943): The railway pattern of metropolitan Chicago. Master and use copy. Digital master created according to Benchmark for Faithful Reproductions of Monographs and Serials, Version 1. Digital Library Federation, December 2002. http://www.diglib.org/standards/bmarkfin.htm')

    def test_get_encoding(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['encoding'], 'Electronic reproduction.')

    def test_get_height(self):
        """Be sure the object can return the Schema dictionary. Testing with Lorem Ipsum random value in record"""
        self.assertEqual(self.collection.schema['height'], 'Dictumst nec duis')

    def test_get_genre(self):
        """Be sure the object can return the Schema dictionary. Testing with Lorem Ipsum random value in record"""
        self.assertEqual(self.collection.schema['genre'], 'Maps. Netus accumsan ornare et')

    def test_get_identifier(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['identifier'], 'CGU')

    def test_get_in_language(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['inLanguage'], 'Eng')

    def test_get_is_accessible_for_free(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['isAccessibleForFree'], 'Digital version available with restrictions Unrestricted online access')

    def test_get_is_part_of(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['isPartOf'], ['(Social scientists map Chicago); (University of Chicago Digital Preservation Collection)', 'Social scientists map Chicago. University of Chicago Digital Preservation Collection.', 'Thematic'])

    def test_get_location_created(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['locationCreated'], '[Chicago] :')

    def test_get_map_type(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['mapType'], 'Thematic maps')

    def test_get_name(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['name'], 'Functional pattern of the railways in Metropolitan Chicago /')

    def test_get_publisher(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['publisher'], '[publisher not identified],')

    def test_get_spatial_coverage(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['spatialCoverage'], 'Scale [ca. 1:580,000] (W 88°30ʹ00ʺ--W 86°44ʹ00ʺ/N 42°46ʹ00ʺ--N 41°17ʹ00ʺ).')

    def test_get_temporal_coverage(self):
        """Be sure the object can return the Schema dictionary. Testing with Lorem Ipsum random value in record"""
        self.assertEqual(self.collection.schema['temporalCoverage'], 'Metus feugiat sollicitudin')

    def test_get_url(self):
        """Be sure the object can return the Schema dictionary."""
        self.assertEqual(self.collection.schema['url'], 'http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6P3-1943-M21')

    def test_get_width(self):
        """Be sure the object can return the Schema dictionary. Testing with Lorem Ipsum random value in record"""
        self.assertEqual(self.collection.schema['width'], 'Dictumst nec duis')
'''

if __name__ == '__main__':
    unittest.main()
