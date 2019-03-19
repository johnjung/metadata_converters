import json
import re
import sys
import xml.etree.ElementTree as ElementTree

from marcxml_converter import MarcXmlConverter

class MarcXmlToSchemaDotOrg(MarcXmlConverter):
  def json(self):
    """
       Returns:
       JSON-LD.
   """
    schema = {}
  
    schema['@context'] = 'https://schema.org'
  
    schema['@type']    = 'Map'
  
    # e.g., http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-2B8-1923-U5
    schema['url']      = next(iter(self.get_marc_field('856', 'u')), None)
  
    schema['name']     = ' '.join(self.get_marc_field('245', 'a') + self.get_marc_field('245', 'b'))
  
    # creator/@type is either 'Organization' or 'Person'.
    creator_type = 'Person' if self.get_marc_field('100') else 'Organization'
  
    # get creators from the 100, 110, or 111 fields if possible. Otherwise get them from the 245c.
    creators = self.get_marc_field('100') + self.get_marc_field('110') + self.get_marc_field('111')
    if not creators:
      creators = self.get_marc_field('245', 'c')
  
    if len(creators) == 1:
      schema['creator'] = {
        '@type': creator_type,
        'name': creators[0]
      }
    else:
      schema_creator = []
      for creator in creators:
        schema_creator.append({
          '@type': creator_type,
          'name': creator
        }) 
      schema['creator'] = schema_creator
  
    schema['description'] = ' '.join(self.get_marc_field('255') + self.get_marc_field('500') + self.get_marc_field('538'))

    return schema

  def __str__(self):
    return json.dumps(self.json())
    
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
      ).json()
    )
  sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=4))
