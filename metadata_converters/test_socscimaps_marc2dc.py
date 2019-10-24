import unittest
import xml.etree.ElementTree as ElementTree
from dc import MarcToDc


ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')


marcxml_str = """<?xml version="1.0" encoding="UTF-8"?>
<collection xmlns="http://www.loc.gov/MARC21/slim">
<record>
  <leader>02946cem a2200529Ii 4500</leader>
  <controlfield tag="001">11435670</controlfield>
  <controlfield tag="003">ICU</controlfield>
  <controlfield tag="005">20180306095826.0</controlfield>
  <controlfield tag="006">m    go  c        </controlfield>
  <controlfield tag="007">aj aanzn</controlfield>
  <controlfield tag="007">cr cn||||||aap</controlfield>
  <controlfield tag="007">cr cn||||||aba</controlfield>
  <controlfield tag="008">180222s1932    ilu       a   o 1   eng d</controlfield>
  <datafield tag="040" ind1=" " ind2=" ">
   <subfield code="a">CGU</subfield>
   <subfield code="b">eng</subfield>
   <subfield code="e">rda</subfield>
   <subfield code="c">CGU</subfield>
   <subfield code="d">CGU</subfield>
  </datafield>
  <datafield tag="034" ind1="1" ind2=" ">
   <subfield code="a">a</subfield>
   <subfield code="b">175300</subfield>
   <subfield code="d">W0875104</subfield>
   <subfield code="e">W0873125</subfield>
   <subfield code="f">N0420123</subfield>
   <subfield code="g">N0413839</subfield>
  </datafield>
  <datafield tag="035" ind1=" " ind2=" ">
   <subfield code="a">(OCoLC)1023863591</subfield>
  </datafield>
  <datafield tag="043" ind1=" " ind2=" ">
   <subfield code="a">n-us-il</subfield>
  </datafield>
  <datafield tag="050" ind1=" " ind2="4">
   <subfield code="a">G4104.C6F7 1880</subfield>
   <subfield code="b">.U5 1932</subfield>
  </datafield>
  <datafield tag="052" ind1=" " ind2=" ">
   <subfield code="a">4104</subfield>
   <subfield code="b">C6</subfield>
  </datafield>
  <datafield tag="072" ind1=" " ind2="7">
   <subfield code="a">F7</subfield>
   <subfield code="2">lcg</subfield>
  </datafield>
  <datafield tag="049" ind1=" " ind2=" ">
   <subfield code="a">CGUA</subfield>
  </datafield>
  <datafield tag="110" ind1="2" ind2=" ">
   <subfield code="a">University of Chicago.</subfield>
   <subfield code="b">Social Science Research Committee.</subfield>
  </datafield>
  <datafield tag="245" ind1="1" ind2="0">
   <subfield code="a">Map of Chicago, showing original subdivisions, 1880 to 1932 /</subfield>
   <subfield code="c">prepared by Homer Hoyt from ante-fire plats of the Chicago Title and Trust Company.</subfield>
  </datafield>
  <datafield tag="255" ind1=" " ind2=" ">
   <subfield code="a">Scale approximately 1:175,300</subfield>
   <subfield code="c">(W 87°51ʹ04ʺ--W 87°31ʹ25ʺ/N 42°01ʹ23ʺ--N 41°38ʹ39ʺ).</subfield>
  </datafield>
  <datafield tag="264" ind1=" " ind2="1">
   <subfield code="a">Chicago :</subfield>
   <subfield code="b">Social Science Research Committee,</subfield>
   <subfield code="c">[1932]</subfield>
  </datafield>
  <datafield tag="300" ind1=" " ind2=" ">
   <subfield code="a">1 online resource (1 map)</subfield>
  </datafield>
  <datafield tag="336" ind1=" " ind2=" ">
   <subfield code="a">cartographic image</subfield>
   <subfield code="b">cri</subfield>
   <subfield code="2">rdacontent</subfield>
  </datafield>
  <datafield tag="337" ind1=" " ind2=" ">
   <subfield code="a">computer</subfield>
   <subfield code="b">c</subfield>
   <subfield code="2">rdamedia</subfield>
  </datafield>
  <datafield tag="338" ind1=" " ind2=" ">
   <subfield code="a">online resource</subfield>
   <subfield code="b">cr</subfield>
   <subfield code="2">rdacarrier</subfield>
  </datafield>
  <datafield tag="506" ind1=" " ind2=" ">
   <subfield code="a">Digital version available with restrictions</subfield>
   <subfield code="f">Unrestricted online access</subfield>
   <subfield code="5">ICU</subfield>
   <subfield code="2">star</subfield>
  </datafield>
  <datafield tag="538" ind1=" " ind2=" ">
   <subfield code="a">Master and use copy. Digital master created according to Benchmark for Faithful Reproductions of Monographs and Serials, Version 1. Digital Library Federation, December 2002.</subfield>
   <subfield code="u">http://www.diglib.org/standards/bmarkfin.htm</subfield>
  </datafield>
  <datafield tag="583" ind1="1" ind2=" ">
   <subfield code="a">digitized</subfield>
   <subfield code="c">2006</subfield>
   <subfield code="h">University of Chicago Library</subfield>
   <subfield code="l">committed to preserve</subfield>
   <subfield code="5">ICU</subfield>
   <subfield code="2">pda</subfield>
  </datafield>
  <datafield tag="533" ind1=" " ind2=" ">
   <subfield code="a">Electronic reproduction.</subfield>
   <subfield code="b">[Chicago] :</subfield>
   <subfield code="c">University of Chicago Library,</subfield>
   <subfield code="d">[2006].</subfield>
   <subfield code="f">(Social scientists map Chicago); (University of Chicago Digital Preservation Collection)</subfield>
   <subfield code="5">ICU</subfield>
  </datafield>
  <datafield tag="651" ind1=" " ind2="0">
   <subfield code="a">Chicago (Ill.)</subfield>
   <subfield code="x">Administrative and political divisions</subfield>
   <subfield code="v">Maps.</subfield>
  </datafield>
  <datafield tag="655" ind1=" " ind2="7">
   <subfield code="a">Thematic maps.</subfield>
   <subfield code="2">lcgft</subfield>
  </datafield>
  <datafield tag="650" ind1=" " ind2="7">
   <subfield code="a">Administrative and political divisions.</subfield>
   <subfield code="2">fast</subfield>
   <subfield code="0">http://id.worldcat.org/fast/fst00796826</subfield>
  </datafield>
  <datafield tag="651" ind1=" " ind2="7">
   <subfield code="a">Illinois</subfield>
   <subfield code="z">Chicago.</subfield>
   <subfield code="2">fast</subfield>
   <subfield code="0">http://id.worldcat.org/fast/fst01204048</subfield>
  </datafield>
  <datafield tag="655" ind1=" " ind2="7">
   <subfield code="a">Maps.</subfield>
   <subfield code="2">fast</subfield>
   <subfield code="0">http://id.worldcat.org/fast/fst01423704</subfield>
  </datafield>
  <datafield tag="655" ind1=" " ind2="7">
   <subfield code="a">Thematic maps.</subfield>
   <subfield code="2">fast</subfield>
   <subfield code="0">http://id.worldcat.org/fast/fst01752679</subfield>
  </datafield>
  <datafield tag="700" ind1="1" ind2=" ">
   <subfield code="a">Hoyt, Homer,</subfield>
   <subfield code="d">1895-1984.</subfield>
  </datafield>
  <datafield tag="776" ind1="0" ind2="8">
   <subfield code="i">Original paper version:</subfield>
   <subfield code="a">University of Chicago. Social Science Research Committee.</subfield>
   <subfield code="t">[Thematic maps of Chicago].</subfield>
   <subfield code="d">[Chicago] : Social Science Research Committee, University of Chicago, [1930-1935]</subfield>
   <subfield code="h">114 maps on 169 sheets ; sheets 29 x 22 cm.</subfield>
   <subfield code="w">(OCoLC)269021352</subfield>
  </datafield>
  <datafield tag="830" ind1=" " ind2="0">
   <subfield code="a">Social scientists map Chicago.</subfield>
   <subfield code="5">ICU</subfield>
  </datafield>
  <datafield tag="830" ind1=" " ind2="0">
   <subfield code="a">University of Chicago Digital Preservation Collection.</subfield>
   <subfield code="5">ICU</subfield>
  </datafield>
  <datafield tag="830" ind1=" " ind2="0">
   <subfield code="a">Social Science Research Committee maps of Chicago.</subfield>
   <subfield code="5">ICU</subfield>
  </datafield>
  <datafield tag="856" ind1="4" ind2="0">
   <subfield code="u">http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-1933-U5-d</subfield>
  </datafield>
  <datafield tag="035" ind1=" " ind2=" ">
   <subfield code="a">1023863591</subfield>
  </datafield>
  <datafield tag="928" ind1=" " ind2=" ">
   <subfield code="u">http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-1933-U5-d</subfield>
   <subfield code="c">FullText</subfield>
   <subfield code="l">Online</subfield>
   <subfield code="t">LCC</subfield>
   <subfield code="a">G4104.C6F7 1880 .U5 1932</subfield>
  </datafield>
 </record>
</collection>"""


class TestMarcToDc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = ElementTree.fromstring(marcxml_str)
        self.dc = MarcToDc(marcxml_str)

    def test_exclude_filter_datafield(self):
        for datafield in self.collection.findall('.//{http://www.loc.gov/MARC21/slim}datafield'):
            if datafield.get('tag') == '650':
                self.assertTrue(
                    self.dc._filter_datafield(datafield, {"subfield_re": "2", "value_re": "^fast$"})
                )

    def test_get_subfield_values(self):
        self.assertEqual(
            self.dc._get_datafield_values(
                self.collection.find('{http://www.loc.gov/MARC21/slim}record'),
                {
                    "exclude": [],
                    "filter": [],
                    "indicator1_re": ".",
                    "indicator2_re": ".",
                    "join_subfields": True,
                    "join_fields": False,
                    "return_first_result_only": False,
                    "subfield_re": "u",
                    "tag_re": "928",
                }
            ),
            ['http://pi.lib.uchicago.edu/1001/maps/chisoc/G4104-C6-1933-U5-d']
        )


if __name__=="__main__":
    unittest.main()
