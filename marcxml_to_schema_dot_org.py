import json
import re
import sys
import xml.etree.ElementTree as ElementTree

from marcxml_converter import MarcXmlConverter


class MarcXmlToSchemaDotOrg(MarcXmlConverter):


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


  def __init__(self, record_str):
    """
       Parameters:
       record_str -- a marcxml record, as a string.
    """
    for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
      if repeat_dc == False:
        assert repeat_sf == False
    super().__init__(record_str)


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

 
  def to_dict(self):
    dict = {
      '@context':    'https://schema.org',
      '@type':       'Map',
      'creator':     self.get_creator()
    }
    for k in dict.keys():
      if dict[k] == None:
        dict.pop(k)

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
            dict[schema_element] = list(field_texts)[0]
          elif len(field_texts) > 1:
            dict[schema_element] = list(field_texts)
        else:
          for marc_field in marc_fields:
            field_text = ' '.join(self.get_marc_field(*marc_field))
            if strip_out:
              field_text = re.sub(strip_out, '', field_text)
            if field_text:
              field_texts.add(field_text)
          if len(field_texts) == 1:
            dict[schema_element] = list(field_texts)[0]
          elif len(field_texts) > 1:
            dict[schema_element] = list(field_texts)
      else:
        field_text_arr = []
        for marc_field in marc_fields:
          field_text_arr = field_text_arr + self.get_marc_field(*marc_field)
        field_text = ' '.join(field_text_arr)
        if strip_out:
          field_text = re.sub(strip_out, '', field_text)
        if field_text:
          dict[schema_element] = field_text

    return dict


  def __str__(self):
    """
       Returns:
       JSON-LD.
    """
    return json.dumps(
      self.to_dict(),
      ensure_ascii=False,
      indent=4
    )

    
if __name__ == '__main__':
  sys.stdout.write(str(MarcXmlToSchemaDotOrg(sys.stdin.read())))
