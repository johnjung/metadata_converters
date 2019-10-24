#!/usr/bin/env python

import copy, json, re, sys
import xml.etree.ElementTree as ElementTree
from classes import MarcXmlConverter


""" If any exclude condition is met, the item will be excluded. If any filter
    condition is met, the item will be filtered. """


class MarcToDc:
    def __init__(self, marcxml):
        ElementTree.register_namespace(
            'dc', 'http://purl.org/dc/elements/1.1/')
        ElementTree.register_namespace(
            'dcterms', 'http://purl.org/dc/terms/')
        self.record = ElementTree.fromstring(marcxml).find(
            '{http://www.loc.gov/MARC21/slim}record')
        with open('socscimaps_marc2dc.json') as f:
            data = json.load(f)
            self.template = data['template']
            self.crosswalk = data['crosswalk']

    def _filter_datafield(self, datafield, r):
        """Return true if any subfields exist that match the conditions in r. 

        Args:
            datafield (xml.etree.ElementTree.Element): a MARCXML datafield element.
            r (dict): a rule, e.g.: { "subfield_re": "2", "value_re": "^fast$" }

        Returns:
            bool: datafield matches. 
        """
        for subfield in datafield.findall('{http://www.loc.gov/MARC21/slim}subfield'):
            if re.search(r['subfield_re'], subfield.get('code')) and \
               re.search(r['value_re'], subfield.text):
                return True
        return False

    def _get_subfield_values(self, datafield, r):
        """
        Return true if any subfields exist that match the conditions in r. 

        Args:
            datafield (xml.etree.ElementTree.Element): a MARCXML datafield element.
            r (dict): a rule, e.g.: { "tag_re": "700", "subfield_re": "a" }

        Returns:
            A list of strings. 
        """
        values = []
        for subfield in datafield.findall('{http://www.loc.gov/MARC21/slim}subfield'):
            if re.search(r['subfield_re'], subfield.get('code')):
                values.append(subfield.text)
        return values

    def _get_datafield_values(self, record, r):
        """Return a list of values for a datafield. Only process datafields
        with the appropriate tag and indicator values.

        Args:
            record (xml.etree.ElementTree.Element): a MARCXML record element.
            r (dict): a rule, e.g. { "tag_re": "700", "subfield_re": "a" }

        Returns:
            A list of strings.
        """
        values = []
        for datafield in record.findall('{http://www.loc.gov/MARC21/slim}datafield'):
            if re.search(r['tag_re'], datafield.get('tag')) == None:
                continue
            if re.search(r['indicator1_re'], datafield.get('ind1')) == None:
                continue
            if re.search(r['indicator2_re'], datafield.get('ind2')) == None:
                continue

            _exclude = False
            for e in r['exclude']:
                if self._filter_datafield(datafield, e):
                    _exclude = True
            if _exclude:
                return []
  
            _filter = True
            if r['filter']:
                _filter = False
                for f in r['filter']:
                    if self._filter_datafield(datafield, f):
                        _filter = True
            if not _filter:
                return []
     
            if r['join_subfields']:
                values.append(' '.join(self._get_subfield_values(datafield, r)))
            else:
                values.extend(self._get_subfield_values(datafield, r))
        if r['return_first_result_only'] and values:
            return [values[0]]
        elif r['join_fields']:
            return [' '.join(values)]
        else:
            return values
            
    def __str__(self):
        metadata = ElementTree.Element('metadata')
        for e, rules in self.crosswalk.items():
            values = []
            for r in rules:
                values.extend(
                    self._get_datafield_values(
                        self.record,
                        {**self.template, **r}
                    )
                )
            element_str = e.replace('dc:', '{http://purl.org/dc/elements/1.1/}').replace('dcterms:', '{http://purl.org/dc/terms/}')
            for value in values:
                ElementTree.SubElement(
                    metadata,
                    element_str
                ).text = value
        return ElementTree.tostring(metadata, 'utf-8', method='xml').decode('utf-8')

if __name__=='__main__':
    ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')
    for record in ElementTree.fromstring(
        sys.stdin.read()
    ).findall('{http://www.loc.gov/MARC21/slim}record'):
        sys.stdout.write(
            str(
                MarcToDc(
                    '<collection>{}</collection>'.format(
                        ElementTree.tostring(record, 'utf-8', method='xml').decode('utf-8')
                    )
                )
            )
        )
        sys.stdout.write('\n')
        sys.exit()
