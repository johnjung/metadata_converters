import unittest
from pathlib import Path
from metadata_converters import MarcXmlConverter, MarcToDc, MarcXmlToSchemaDotOrg


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
        with open(file, 'r') as f:
            data = f.read().replace('\n', '')
            self.assertTrue(len(data) > 0)
        self.collection = MarcXmlConverter(data)
        self.assertEqual(str(type(self.collection.record)), "<class 'xml.etree.ElementTree.Element'>")
        #self.assertEqual(self.collection.get_marc_field('655', '', '', ''), ['Thematic maps.', 'lcgft'])

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


class TestMarcToDc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        """Create test objects. Test data should be placed in the test_data
        directory of this project. It should include sample data from different
        digital collections projects, and the data should be varied enough to 
        be able to catch different kinds of edge cases in testing."""
        super().__init__(*args, **kwargs)
        self.test_init()

    def test_init(self):
        """MarcToDc extends the MarcXmlConverter class and should have a .record property which is a
        xml.etree.ElementTree.Element."""
        file = Path('test_data/sample_record_02.xml')
        with open(file, 'r') as f:
            data = f.read().replace('\n', '')
            self.assertTrue(len(data) > 0)
        self.collection = MarcToDc(data)

    def test_get_rights_access(self):
        """Be sure the object can return the DC element."""
        print(str(self.collection))
        self.assertEqual(self.collection.identifier, 'temp')
'''
    def test_get_contributor(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_coverage(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_creator(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_date_copyrighted(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_description(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    #def test_get_format.extent(self):
        """Be sure the object can return the DC element."""
    #    raise NotImplementedError

    def test_get_format(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_relation_has_format(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_identifier(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_relation_is_part_of(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_date_issued(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_language(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_coverage_location(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_format_medium(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_coverage_period_of_time(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_publisher(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_relation(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_subject(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_subject(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_title(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError

    def test_get_type(self):
        """Be sure the object can return the DC element."""
        raise NotImplementedError
'''

if __name__ == '__main__':
    unittest.main()