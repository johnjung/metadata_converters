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
  
    schema['@type'] = 'Map'
  
    # e.g., http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-2B8-1923-U5
    schema['url'] = next(iter(self.get_marc_field('856', 'u', '.', '.')), None)
 
    name_str = ' '.join(self.get_marc_field('245', '[ab]', '.', '.'))
    if name_str:
      schema['name'] = name_str
  
    # creator/@type is either 'Organization' or 'Person'.
    if self.get_marc_field('100', '[a-z]', '.', '.'):
      creator_type = 'Person'
    else:
      creator_type = 'Organization'
  
    # get creators from the 100, 110, or 111 fields if possible. 
    # Otherwise get them from the 245c.
    creators = []
    creator_str = ' '.join(self.get_marc_field('100', '[a-z]', '.', '.'))
    if creator_str:
      creators.append(creator_str)
    creator_str = ' '.join(self.get_marc_field('110', '[a-z]', '.', '.'))
    if creator_str:
      creators.append(creator_str)
    creator_str = ' '.join(self.get_marc_field('111', '[a-z]', '.', '.'))
    if creator_str:
      creators.append(creator_str)
    if not creators:
      creators = [' '.join(self.get_marc_field('245', 'c', '.', '.'))]
  
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
      if schema_creator:
        schema['creator'] = schema_creator
 
    description_str = ' '.join(
      self.get_marc_field('255', '[a-z]', '.', '.') + \
      self.get_marc_field('500', '[a-z]', '.', '.') + \
      self.get_marc_field('538', '[a-z]', '.', '.')
    )
    if description_str:
      schema['description'] = description_str

    identifier = self.get_marc_field('001', '.', '.', '.')
    if identifier:
      schema['identifier'] = 'http://pi.lib.uchicago.edu/1001/cat/bib/{}'.format(identifier[0])

    publishers = self.get_marc_field('264', 'b', '1', '.')
    if publishers:
      schema['publisher']

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
