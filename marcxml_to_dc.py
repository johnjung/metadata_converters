import re
import sys
import xml.etree.ElementTree as ElementTree

from marcxml_converter import MarcXmlConverter

class MarcToDc(MarcXmlConverter):
  ''' mappings -- a list of tuples-
        [0] -- Dublin Core metadata element.
        [1] -- a list-
          [0] a boolean, DC element is repeatable. 
          [1] a list, a MARC field specification-
            [0] a string, the MARC field itself.
            [1] a regular expression (as a string), allowable subfields. 
            [2] a regular expression (as a string), indicator 1.
            [3] a regular expression (as a string), indicator 2. 
	  [2] a boolean, subfields repeat. 
              assert [2]==False if [0]==False.
	  [3] a regular expression (as a string) to strip out of the field, or
              None if there is nothing to exclude.
              if the resulting value is '' it won't be added.
  '''

  mappings = [
    ('dc:accessRights',    [False, [('506', '[a-z]',  '.', '.')], False,   None]),
    ('dc:contributor',     [True,  [('700', 'a',      '.', '.'),
                                    ('710', 'a',      '.', '.')], False,   None]),   
    ('dc:coverage',        [False, [('255', '[a-z]',  '.', '.')], False,   None]),
    ('dc:creator',         [True,  [('100', '[a-z]',  '.', '.'),
                                    ('110', '[a-z]',  '.', '.'),
                                    ('111', '[a-z]',  '.', '.'),
                                    ('245', 'c',      '.', '.')], False,   None]),
    ('dc:dateCopyrighted', [True,  [('264', 'c',      '.', '4')], False,   None]),
    ('dc:description',     [False, [('300', '[a-z3]', '.', '.')], False,   None]),
    ('dc:extent',          [False, [('300', '[a-z]',  '.', '.')], False,   None]),
    ('dc:format',          [True,  [('337', 'a',      '.', '.')], False,   '^computer$']),
    ('dc:hasFormat',       [True,  [('533', 'a',      '.', '.')], False,   None]),
    ('dc:identifier',      [True,  [('020', '[a-z]',  '.', '.'),
                                    ('021', '[a-z]',  '.', '.'),
                                    ('022', '[a-z]',  '.', '.'),
                                    ('023', '[a-z]',  '.', '.'),
                                    ('024', '[a-z]',  '.', '.'),
                                    ('025', '[a-z]',  '.', '.'),
                                    ('026', '[a-z]',  '.', '.'),
                                    ('027', '[a-z]',  '.', '.'),
                                    ('028', '[a-z]',  '.', '.'),
                                    ('029', '[a-z]',  '.', '.'),
                                    ('856', 'u',      '.', '.')], True,    None]),
    ('dc:isPartOf',        [True,  [('490', '[a-z]',  '.', '.'),
                                    ('533', 'f',      '.', '.'),
                                    ('700', 't',      '.', '.'),
                                    ('830', '[a-z]',  '.', '.')], False,   None]),
    ('dc:issued',          [True,  [('264', 'c',      '1', '.')], False,   None]),
    ('dc:language',        [True,  [('041', '[a-z]',  '.', '.')], True,    None]),
    ('dc:location',        [True,  [('264', 'a',      '1', '.'),
                                    ('533', 'b',      '.', '.')], False,   None]),
    ('dc:medium',          [True,  [('338', '[a-z]',  '.', '.')], False,   None]),
    ('dc:periodOfTime',    [True,  [('650', 'y',      '.', '.')], False,   None]),
    ('dc:publisher',       [True,  [('264', 'b',      '1', '.')], False,   None]),
    ('dc:relation',        [True,  [('730', 'a',      '.', '.')], False,   None]),
    ('dc:subject',         [True,  [('050', '[a-z]',  '.', '.')], False,   '[. ]*$']),
    ('dc:subject',         [True,  [('650', '[ax]',   '.', '.')], True,    '[. ]*$']),
    ('dc:title',           [True,  [('130', '[a-z]',  '.', '.'), 
                                    ('240', '[a-z]',  '.', '.'),
                                    ('245', '[ab]',   '.', '.'),
                                    ('246', '[a-z]',  '.', '.')], False,   None]),
    ('dc:type',            [True,  [('336', '[a-z]',  '.', '.'),
                                    ('650', 'v',      '.', '.'),
                                    ('651', 'v',      '.', '.'),
                                    ('655', 'a',      '.', '.')], True,    '^Maps[. ]*$'])
  ]


  def __init__(self, record_str):
    """
       Parameters:
       record_str -- a marcxml record, as a string.
    """
    for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
      if repeat_dc == False:
        assert repeat_sf == False
    super().__init__(record_str)

 
  def xml(self):
    """
       Returns:
       XML dublin core data. 
    """
    ElementTree.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')

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
              dc_element.replace('dc:', '{http://purl.org/dc/elements/1.1/}')
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
              dc_element.replace('dc:', '{http://purl.org/dc/elements/1.1/}')
            ).text = field_text
      else:
        field_text_arr = []
        for marc_field in marc_fields:
          field_text_arr = field_text_arr + self.get_marc_field(*marc_field)
        field_text = ' '.join(field_text_arr)
        if strip_out:
          field_text = re.sub(strip_out, '', field_text)
        if field_text:
          ElementTree.SubElement(
            metadata,
            dc_element.replace('dc:', '{http://purl.org/dc/elements/1.1/}')
          ).text = field_text

    # thomas 1:12 post. 
    # 655 handling:
    # discard if subfield 2 == 'lcgft'

    return metadata


  def __str__(self):
    """
       Returns:
       XML dublin core data as a string.
    """

    return ElementTree.tostring(self.xml(), 'utf-8', method='xml').decode('utf-8')


if __name__ == '__main__':
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

  marcxml = ElementTree.fromstring(sys.stdin.read())

  dublin_core = ElementTree.Element('dublin_core')
  for record in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
    dublin_core.append(
      MarcToDc(
        ElementTree.tostring(
          record, 
          'utf-8', 
          method='xml'
        ).decode('utf-8')
      ).xml()
    )
  indent(dublin_core)
  ElementTree.dump(dublin_core)
