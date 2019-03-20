import re
import xml.etree.ElementTree as ElementTree

class MarcXmlConverter:
  def __init__(self, record_str):
    """
       Parameters:
       record_str -- a marcxml record, as a string.
    """
    self.record = ElementTree.fromstring(record_str)


  def get_marc_field(self, field_tag, subfield_code, ind1, ind2): 
    """
       Parameters:
       field_tag     -- a string, e.g. '245'
       subfield_code -- a regular expression (as a string), e.g. '[a-z]'
       ind1          -- a regular expression (as a string), e.g. '4'
       ind2          -- a regular expression (as a string), e.g. '5'
 
       Returns:
       A list of strings, the values of all MARC tags and subfields that matched. 
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
