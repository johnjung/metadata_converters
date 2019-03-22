import json
import re
import sys
import xml.etree.ElementTree as ElementTree

from marcxml_converter import MarcXmlConverter


class MarcXmlToSchemaDotOrg(MarcXmlConverter):


  def get_creator(self):
    '''
       Get creators from the 100, 110, or 111 fields if possible. 
       Otherwise get them from the 245c.
    '''
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

 
  def get_description(self):
    l = []
    for m in ('255', '500', '538'):
      l = l + self.get_marc_field(m, '[a-z]', '.', '.')
    return ' '.join(l) or None


  def get_identifier(self):
    return next(iter(self.get_marc_field('001', '.', '.', '.')), None)


  def get_name(self):
    return ' '.join(self.get_marc_field('245', '[ab]', '.', '.')) or None


  def get_url(self):
   return next(iter(self.get_marc_field('856', 'u', '.', '.')), None)


  def to_dict(self):
    dict = {
      '@context':    'https://schema.org',
      '@type':       'Map',
      'url':         self.get_url(),
      'name':        self.get_name(),
      'creator':     self.get_creator(),
      'description': self.get_description(),
      'identifier':  self.get_identifier()
    }
    for k in dict.keys():
      if dict[k] == None:
        dict.pop(k)
    return dict


  def __str__(self):
    """
       Returns:
       JSON-LD.
   """

    return json.dumps(self.to_dict())

    
if __name__ == '__main__':
  marcxml = ElementTree.fromstring(sys.stdin.read())

  output = []
  for record in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
    output.append(
      MarcXmlToSchemaDotOrg(
        ElementTree.tostring(
          record, 
          'utf-8', 
          method='xml'
        ).decode('utf-8')
      ).to_dict()
    )
  sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=4))
