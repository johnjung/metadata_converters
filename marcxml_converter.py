import xml.etree.ElementTree as ElementTree

class MarcXmlConverter:
  def __init__(self, record_str):
    """
       Parameters:
       record_str -- a marcxml record, as a string.
    """
    self.record = ElementTree.fromstring(record_str)


  def get_marc_field(self, field_tag, subfield_code=None, ind1=None, ind2=None): 
    """
       Parameters:
       field_tag     -- a string, e.g. '245'
       subfield_code -- a string, e.g. 'a', or None
       ind1          -- a string, e.g. '4', or None
       ind2          -- a string, e.g. '5', or None
    """
    results = []
    for element in self.record:
      try:
        if element.attrib['tag'] != field_tag:
          continue
      except KeyError:
        continue
      if element.tag == '{http://www.loc.gov/MARC21/slim}controlfield':
        results.append(element.text)
      elif element.tag == '{http://www.loc.gov/MARC21/slim}datafield':
        try:
          if ind1 and element.attrib['ind1'] != ind1:
            continue
          if ind2 and element.attrib['ind2'] != ind2:
            continue
        except KeyError:
          continue
        for subfield in element:
          if subfield_code:
            if subfield.attrib['code'] == subfield_code:
              results.append(subfield.text)
          else:
            results.append(subfield.text)
    return results
