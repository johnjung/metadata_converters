import re
import sys
import xml.etree.ElementTree as ElementTree

from marcxml_converter import MarcXmlConverter

class MarcToDc(MarcXmlConverter):
  mappings = {  
    'dc:accessRights'    : [('506', None, None, None)],
    'dc:contributor'     : [('700', 'a',  None, None), 
                            ('710', 'a',  None, None)],
    'dc:coverage'        : [('034', None, None, None),
                            ('043', None, None, None),
                            ('052', None, None, None),
                            ('650', 'z',  None, None),
                            ('651', 'a',  None, None), 
                            ('651', 'z',  None, None)],
    'dc:creator'         : [('100', None, None, None),
                            ('110', None, None, None),
                            ('111', None, None, None),
                            ('245', 'c',  None, None),
                            ('533', 'c',  None, None)], 
    'dc:date'            : [('533', 'd',  None, None)],
    'dc:dateCopyrighted' : [('264', 'c',  None, '4' )],
    'dc:description'     : [('500', None, None, None),
                            ('538', None, None, None)],
    'dc:extent'          : [('300', 'a',  None, None),
                            ('300', 'c',  None, None)],
    'dc:format'          : [('337', None, None, None)],
    'dc:hasFormat'       : [('533', 'a',  None, None), 
                            ('776', 'a',  None, None)],
    'dc:identifier'      : [('020', None, None, None),
                            ('021', None, None, None),
                            ('022', None, None, None), 
                            ('023', None, None, None), 
                            ('024', None, None, None),
                            ('025', None, None, None),
                            ('026', None, None, None),
                            ('027', None, None, None), 
                            ('028', None, None, None),
                            ('029', None, None, None),
                            ('856', 'u',  None, None)],
    'dc:isPartOf'        : [('490', None, None, None),
                            ('533', 'f',  None, None),
                            ('700', 't',  None, None),
                            ('830', None, None, None)],
    'dc:issued'          : [('264', 'c',  '1',  None)],
    'dc:language'        : [('041', None, None, None)], 
    'dc:location'        : [('264', 'a',  '1',  None),
                            ('533', 'b',  None, None)],
    'dc:medium'          : [('338', None, None, None)],
    'dc:periodOfTime'    : [('650', 'y',  None, None)],
    'dc:publisher'       : [('264', 'b',  '1',  None)],
    'dc:relation'        : [('730', 'a',  None, None)],
    'dc:subject'         : [('050', None, None, None),
                            ('650', 'x',  None, None)],
    'dc:title'           : [('130', None, None, None), 
                            ('240', None, None, None),
                            ('245', 'a',  None, None),
                            ('245'  'b',  None, None),
                            ('246', None, None, None)],
    'dc:type'            : [('336', None, None, None),
                            ('650', 'v',  None, None),
                            ('651', 'v',  None, None),
                            ('655', 'v',  None, None),
                            ('655', '2',  None, None),
                            ('655', 'c',  None, None)]
  }

  def __str__(self):
    """
       Returns:
       XML dublin core data. 
    """
    ElementTree.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')

    metadata = ElementTree.Element('metadata')
    for dc_element, marc_fields in self.mappings.items():
      for marc_field in marc_fields:
        for field_text in self.get_marc_field(*marc_field):
          ElementTree.SubElement(
            metadata,
            dc_element.replace('dc:', '{http://purl.org/dc/elements/1.1/}')
          ).text = field_text
    return ElementTree.tostring(metadata, 'utf-8', method='xml').decode('utf-8')


if __name__ == '__main__':
  marcxml = ElementTree.fromstring(sys.stdin.read())
  sys.stdout.write('<dublin_core>')
  for record in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
    sys.stdout.write(
      str(
        MarcToDc(
          ElementTree.tostring(
            record, 
            'utf-8', 
            method='xml'
          ).decode('utf-8')
        )
      )
    )
  sys.stdout.write('</dublin_core>')
