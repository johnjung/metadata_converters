# -*- coding: utf-8 -*-
import pymarc, sys, unittest
from metadata_converters import SocSciMapsMarcXmlToDc
from pymarc import MARCReader

class TestSocSciMapsMarcXmlToDc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        """See specs for this converter at:
        https://docs.google.com/spreadsheets/d/1Kz1nfTSBjc2PTJ8hrZ--JCBpKV061sdXQxRxVo8VY_Y/edit#gid=0"""

        super().__init__(*args, **kwargs)

        self.mrc = {}
        for m in ('11435665', '3451312', '5999566', '7368094', '7368097', '7641168'):
            with open('./test_data/{}.mrc'.format(m), 'rb') as fh:
                reader = MARCReader(fh)
                for record in reader:
                    self.mrc[m] = record

        self.ns = {
            'bf': 'http://id.loc.gov/ontologies/bibframe/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/',
            'madsrdf': 'http://www.loc.gov/mads/rdf/v1#'
        }

    def test_classification_lcc(self):
        """get bf:ClassificationLcc from 929 $a of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('bf:ClassificationLcc', self.ns).text,
            'G4104.C6:2W9 1920z .U5'
        )

    def test_coordinates(self):
        """get bf:coordinates from the 034 $d $e $f $g

           encode this in the following format: 
           $$c(W 87°51'04"-W 87°31'25"/N 42°01'23"-N 41°38'39")

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('bf:coordinates', self.ns).text,
            '''$$c(W 87°37'49"-W 87°34'20"/N 41°47'12"-N 41°45'53")'''
        )

    def test_corporate_name(self):
        """get madsrdf:CorporateName from 110 or 710 $a.

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('madsrdf:CorporateName', self.ns).text,
            'University of Chicago. Department of Sociology.'
        )

    def test_description(self):
        """get dc:description from 500, 538

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        test_descriptions = set()

        for d in SocSciMapsMarcXmlToDc(
            self.mrc['7641168'],
            self.mrc['3451312'],
            'b2dq0kf6d36z'
        )._asxml().findall('dc:description', self.ns):
            test_descriptions.add(d.text)

        self.assertEqual(
            test_descriptions,
            set((
                'Blue line print.',
                'Shows residential area, vacant area, commercial frontage, railroad property, and transit lines.',
                'Master and use copy. Digital master created according to Benchmark for Faithful Reproductions of Monographs and Serials, Version 1. Digital Library Federation, December 2002. http://www.diglib.org/standards/bmarkfin.htm'
            ))
        )

    def test_format(self):
        """get dc:format from 255 $a $b, 300 $a $c of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        test_formats = set()

        for f in SocSciMapsMarcXmlToDc(
            self.mrc['7641168'],
            self.mrc['3451312'],
            'b2dq0kf6d36z'
        )._asxml().findall('dc:format', self.ns):
            test_formats.add(f.text)

        self.assertEqual(
            test_formats,
            set((
                '1 map',
                '45 x 62 cm'
            ))
        )

    def test_has_format(self):
        """get dcterms:hasFormat from 776 $1

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dcterms:hasFormat', self.ns).text,
            'Print version'
        )

    def test_identifier(self):
        """get dc:identifier from 856 $u

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dc:identifier', self.ns).text,
            'ark:/61001/b2dq0kf6d36z'
        )

    def test_is_part_of(self):
        """get dcterms:isPartOf from 830

           use 11435665.mrc (digital) and 7368097.mrc (print)"""

        test_is_part_ofs = set()

        for i in SocSciMapsMarcXmlToDc(
            self.mrc['11435665'],
            self.mrc['7368097'],
            'b2dq0kf6d36z'
        )._asxml().findall('dcterms:isPartOf', self.ns):
            test_is_part_ofs.add(i.text)

        self.assertEqual(
            test_is_part_ofs,
            set((
                'Social scientists map Chicago.',
                'University of Chicago Digital Preservation Collection.',
                'Social Science Research Committee maps of Chicago.'
            ))
        )

    def test_issued(self):
        """get dcterms:issued from 260$c, 264 _1$c

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dcterms:issued', self.ns).text,
            '1920/1929'
        )

    def test_language(self):
        """get dc:language from the 008

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dc:language', self.ns).text,
            'en'
        )

    def test_local(self):
        """get bf:Local from 001 of linked record

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('bf:Local', self.ns).text,
            'http://pi.lib.uchicago.edu/1001/cat/bib/3451312'
        )

    def test_place(self):
        """get bf:place from 260$a, 264 _1$a

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('bf:place', self.ns).text,
            'Chicago'
        )

    def test_publisher(self):
        """get dc:publisher from 260$b, 264 _1$b

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dc:publisher', self.ns).text,
            'Dept. of Sociology'
        )

    def test_rights_access(self):
        """get dcterms:accessRights from 506

           use 7641168.mrc (digital) and 3451312.mrc (print)"""
        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dcterms:accessRights', self.ns).text,
            'Digital version available with restrictions Unrestricted online access'
        )

    def test_scale(self):
        """get bf:scale from 255 $a

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('bf:scale', self.ns).text,
            'Scale [ca. 1:8,000]'
        )

    def test_spatial(self):
        """get dcterms:spatial from 651 _7 $a $z $2 fast

           use 5999566.mrc (digital) and 7368094.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['5999566'],
                self.mrc['7368094'],
                'b2dq0kf6d36z'
            )._asxml().find('dcterms:spatial', self.ns).text,
            'Illinois -- Chicago'
        )

    def test_subject(self):
        """get dc:subject from 650 $a, $x

           use 5999566.mrc (digital) and 7368094.mrc (print)"""

        test_subjects = set()

        for f in SocSciMapsMarcXmlToDc(
            self.mrc['5999566'],
            self.mrc['7368094'],
            'b2dq0kf6d36z'
        )._asxml().findall('dc:subject', self.ns):
            test_subjects.add(f.text)

        self.assertEqual(
            test_subjects,
            set((
                'Crime',
                'Criminals'
            ))
        )

    def test_title(self):
        """get dc:title from 245 $a $b

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dc:title', self.ns).text,
            'Woodlawn Community /'
        )

    def test_type(self):
        """get dc:type from 336 $a, 650 $v, 651 $v, 655 $2 fast

           use 7641168.mrc (digital) and 3451312.mrc (print)"""

        self.assertEqual(
            SocSciMapsMarcXmlToDc(
                self.mrc['7641168'],
                self.mrc['3451312'],
                'b2dq0kf6d36z'
            )._asxml().find('dc:type', self.ns).text,
            'Maps'
        )

    # def test_alternative_title(self):
    #     """get dcterms:alternative from 246"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_coverage(self):
    #     """get dc:coverage from 651 _7 $a $2 fast"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_date_copyrighted(self):
    #     """get dcterms:dateCopyrighted from 264 _4$c"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_isbn(self):
    #     """get bf:ISBN from the 020"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_issn(self):
    #     """get bf:ISSN from the 022"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_relation(self):
    #     """get dc:relation from 730$a"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_temporal(self):
    #     """get dcterms:temporal from 650 $y"""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError

    # def test_title_uniform(self):
    #     """get mods:titleUniform from the 130 and 240."""
    #     Not available in the Social Scientists maps.
    #     raise NotImplementedError


if __name__ == '__main__':
    unittest.main()
