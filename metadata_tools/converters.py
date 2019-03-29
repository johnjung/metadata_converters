import json
import re
import sys
import xml.etree.ElementTree as ElementTree


class MarcXmlConverter:
  """
  A class to convert MARCXML to other formats. Extend this class to make
  converters for outputting specific formats. 

  :rtype :class:`MarcXmlConverter`
  """
  def __init__(self, marcxml):
    """Initialize an instance of the class MarcXmlConverter.

    :param str marcxml: a marcxml collection with a single record.
    """
    self.record = ElementTree.fromstring(marcxml).find('{http://www.loc.gov/MARC21/slim}record')

    # Only bring in 655's where the $2 subfield is set to 'lcgft'. 
    for element in self.record:
      if element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
        if element.attrib['tag'] == '655':
          for subfield in element:
            if subfield.attrib['code'] == '2' and not subfield.text == 'lcgft':
              self.record.remove(element)
              continue


  def get_marc_field(self, field_tag, subfield_code, ind1, ind2): 
    """Get a specific MARC field. 

    :param str field_tag: e.g., "245"
    :param str subfield_code: subfield codes as a regex, e.g. '[a-z]'
    :param str ind1: first indicator as a regex, e.g. '4'
    :param str ind2: second indicator as a regex, e.g. '4'

    :rtype list
    :returns a list of strings, all matching MARC tags and subfields.
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


class MarcToDc(MarcXmlConverter):
  """
  A class to convert MARCXML to Dublin Core. 

  The Library of Congress MARCXML to DC conversion is here:
  http://www.loc.gov/standards/marcxml/xslt/MARC21slim2SRWDC.xsl
  It produces slightly different results. 

  :rtype :class:`MarcToDc`

  mappings -- a list of tuples-
    [0] -- Dublin Core metadata element.
    [1] -- a list-
      [0] a boolean, DC element is repeatable. 
      [1] a list, a MARC field specification-
        [0] a string, the MARC field itself.
        [1] a regular expression (as a string), allowable subfields. 
        [2] a regular expression (as a string), indicator 1.
        [3] a regular expression (as a string), indicator 2. 
    [2] a boolean, subfields each get their own DC element. If False,
        subfields are joined together into a single DC element.
        assert this field==False if [0]==False.
    [3] a regular expression (as a string) to strip out of the field, or
        None if there is nothing to exclude.
        if the resulting value is '' it won't be added.
  """

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
                                    ('856', 'u',      '.', '.')], False,   None]),
    ('dc:isPartOf',        [True,  [('490', '[a-z]',  '.', '.'),
                                    ('533', 'f',      '.', '.'),
                                    ('700', 't',      '.', '.'),
                                    ('830', '[a-z]',  '.', '.')], False,   None]),
    ('dc:issued',          [True,  [('264', 'c',      '1', '.')], False,   None]),
    ('dc:language',        [True,  [('041', '[a-z]',  '.', '.')], True,    None]),
    ('dc:location',        [True,  [('264', 'a',      '1', '.'),
                                    ('533', 'b',      '.', '.')], False,   None]),
    ('dc:medium',          [True,  [('338', 'a',      '.', '.')], False,   None]),
    ('dc:periodOfTime',    [True,  [('650', 'y',      '.', '.')], False,   None]),
    ('dc:publisher',       [True,  [('264', 'b',      '1', '.')], False,   None]),
    ('dc:relation',        [True,  [('730', 'a',      '.', '.')], False,   None]),
    ('dc:subject',         [True,  [('050', '[a-z]',  '.', '.')], False,   '[. ]*$']),
    ('dc:subject',         [True,  [('650', '[ax]',   '.', '.')], True,    '[. ]*$']),
    ('dc:title',           [True,  [('130', '[a-z]',  '.', '.'), 
                                    ('240', '[a-z]',  '.', '.'),
                                    ('245', '[ab]',   '.', '.'),
                                    ('246', '[a-z]',  '.', '.')], False,   None]),
    ('dc:type',            [True,  [('336', 'a',      '.', '.'),
                                    ('650', 'v',      '.', '.'),
                                    ('651', 'v',      '.', '.'),
                                    ('655', 'a',      '.', '.')], False,   '^Maps[. ]*$|[. ]*$'])
  ]


  def __init__(self, marcxml):
    """Initialize an instance of the class MarcToDc.

    :param str marcxml: a marcxml collection with a single record.
    """
    for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
      if repeat_dc == False:
        assert repeat_sf == False
    super().__init__(marcxml)
    self._build_xml()


  def __getattr__(self, attr):
    """Return individual Dublin Core elements as instance properties, e.g.
    self.identifier.

    :rtype list
    """
    return [t for t in self.dc.findall('{{http://purl.org/dc/elements/1.1/}}{}'.format(attr)).text]


  def _build_xml(self):
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
    self.dc = metadata
  
  
  def __str__(self):
    """Return Dublin Core XML as a string.

    :rtype str
    """
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

    indent(self.dc)
    return ElementTree.tostring(self.dc, 'utf-8', method='xml').decode('utf-8')


class MarcXmlToSchemaDotOrg(MarcXmlConverter):
  """
  A class to convert MARCXML to Schema.org.

  :rtype :class:`MarcToSchemaDotOrg`
  """

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

    :param str marcxml: a marcxml collection with a single record. 
    """
    for _, (repeat_dc, _, repeat_sf, _) in self.mappings:
      if repeat_dc == False:
        assert repeat_sf == False
    super().__init__(marcxml)


  def _get_creator(self):
    """Get creators from the 100, 110, or 111 fields if possible. 
    Otherwise get them from the 245c.

    :rtype dict
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

    :rtype dict
    """
    dict = {
      '@context':    'https://schema.org',
      '@type':       'Map',
      'creator':     self._get_creator()
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
    """Return Schema.org data as a JSON-LD string.

    :rtype str
    """
    return json.dumps(
      self(),
      ensure_ascii=False,
      indent=4
    )
