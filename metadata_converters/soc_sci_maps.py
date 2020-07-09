#!/usr/bin/env python
"""Usage:
    soc_sci_maps --cat-dc <digital_record_id>
    soc-sci_maps --cat-edm <digital_record_id>
    soc_sci_maps --create <digital_record_id>
"""

import io, json, hashlib, os, paramiko, sys
import xml.etree.ElementTree as ElementTree

from classes import NoidManager, SocSciMapsMarcXmlToDc, SocSciMapsMarcXmlToEDM
from docopt import docopt
from PIL import Image
from pymarc import MARCReader

Image.MAX_IMAGE_PIXELS = 1000000000

ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')

# digital records for the social scientists maps. 
# 11435664 11435665 11435666 11435667 11435668 11435669 11435670 11435671
# 11435672 11435673 11435674 11435675 11435676 11435677 11435678 11435679
#  1582888  1582891  1582893  1586198  1586219  3401134  3404181  3450640
#  3450644    39315  5043062  5043187  5043398  5043675  5043919  5059056
#  5063149  5063673  5063697  5063699  5063706  5070204  5077687  5570199
#  5998122  5999564  5999565  5999566  7641168

# this directory contains initial image data.
data_directory = '/data/digital_collections/IIIF/IIIF_Files/maps/chisoc'

# all pair tree data is stored here.
pair_tree_root = '/data/digital_collections'

def get_tiff_dir(data_directory, digital_record_id):
    for subdir in os.listdir(data_directory):
        with open('{0}/{1}/{1}.xml'.format(data_directory, subdir)) as f:
            xml = ElementTree.parse(f)
            for element in xml.find('m:record').findall('m:controlfield'):
                if element.attrib['tag'] == '001':
                    if element.text == digital_record_id:
                        return '{}/{}/tifs'.format(data_directory, subdir)
    raise ValueError

def get_image_data(tiff_directory):
    image_data = []
    for tiff in os.listdir(tiff_directory):
            tiff_path = '{}{}{}'.format(tiff_directory, os.sep, tiff)
            try:
                mime_type = 'image/tiff'
                size = os.path.getsize(tiff_path)
                img = Image.open(tiff_path)
                width = img.size[0]
                height = img.size[1]
            except AttributeError:
                sys.stdout.write('trouble with {}\n'.format(tiff_path))
                sys.exit()
    
            with open(tiff_path, 'rb') as f:
                tiff_contents = f.read()
                md5 = hashlib.md5(tiff_contents).hexdigest()
                sha512 = hashlib.sha512(tiff_contents).hexdigest()

            image_data.append({
                'height': height,
                'md5': md5,
                'mime_type': mime_type,
                'name': '{}.tif'.format(identifier),
                'path': tiff_path,
                'pair_tree_path': pair_tree_path,
                'sha512': sha512,
                'size': size,
                'width': width
            })
    return image_data

def get_catalog_record(url):
    _, ssh_stdout, _ = ssh.exec_command('curl "{}"'.format(url))
    data = json.loads(ssh_stdout.read())
    fullrecord = data['response']['docs'][0]['fullrecord']

    with io.BytesIO(fullrecord.encode('utf-8')) as fh:
        reader = MARCReader(fh)
        for record in reader:
            return record

def get_catalog_record_by_id(id):
    return get_catalog_record(
        'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=id:{}'.format(str(id))
    )

def get_catalog_record_by_oclc_number(oclc_num):
    return get_catalog_record(
        'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=oclc_num:{}'.format(str(oclc_num))
    )

def get_dc_str(digital_record, print_record, noid):
    return str(SocSciMapsMarcXmlToDc(digital_record, print_record, noid))

def get_edm_str(digital_record, print_record, noid):
    # save EDM as a string of triples. 
    edm = SocSciMapsMarcXmlToEDM(
        digital_record,
        print_record,
        noid
        image_data
        get_image_data(
            get_tiff_dir(
                data_directory, 
                options['<digital_record_id>']
            )
        )
    )
    edm.build_item_triples()
    return str(SocSciMapsMarcXmlToEDM.triples())

def create(options, digital_record, print_record, noid):
    # create an SSH object.
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ['SOLR_ACCESS_DOMAIN'],
        username=os.environ['SOLR_ACCESS_USERNAME'],
        password=os.environ['SOLR_ACCESS_PASSWORD']
    )

    # get DC data and EDM triples as strings.
    dc_str = get_dc_str(digital_record, print_record, noid)
    edm_str = get_edm_str(digital_record, print_record, noid)

    # create OCFL directory in pair tree.
    # add files. 

def main():
    options = docopt(__doc__)

    # generate a new, unique noid. 
    noid_manager = NoidManager()
    noid = noid_manager.create()

    # request the digital record
    digital_record = get_record_by_id(options['<digital_record_id>'])

    # request the print record
    print_record = get_record_by_oclc_number(
        digital_record['776']['w'].replace('(OCoLC)', '')
    )

    if options['--cat-dc']:
        sys.stdout.write(get_dc_str(digital_record, print_record, noid))
    elif options['--cat-edm']:
        sys.stdout.write(get_edm_str(digital_record, print_record, noid))
    elif options['--create']:
        create()

if __name__ == "__main__":
    main()
