#!/usr/bin/env python
"""Usage:
    marc2edm (--socscimaps <digital_record_id>|--socscimaps-project-triples)
"""

import io, json, hashlib, os, paramiko, sys
import xml.etree.ElementTree as ElementTree
from classes import SocSciMapsMarcXmlToEDM
from docopt import docopt
from PIL import Image
from pymarc import MARCReader

Image.MAX_IMAGE_PIXELS = 1000000000

def main():
    options = docopt(__doc__)

    if options['--socscimaps']:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            os.environ['SOLR_ACCESS_DOMAIN'],
            username=os.environ['SOLR_ACCESS_USERNAME'],
            password=os.environ['SOLR_ACCESS_PASSWORD']
        )
    
        # request the digital record
        url = 'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=id:{}'.format(str(options['<digital_record_id>']))
        _, ssh_stdout, _ = ssh.exec_command('curl "{}"'.format(url))
        data = json.loads(ssh_stdout.read())
        fullrecord = data['response']['docs'][0]['fullrecord']
    
        with io.BytesIO(fullrecord.encode('utf-8')) as fh:
            reader = MARCReader(fh)
            for record in reader:
                digital_record = record
    
        # get an oclc number for the print record
        oclc_num = digital_record['776']['w'].replace('(OCoLC)', '')
    
        # request the print record
        url = 'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=oclc_num:{}'.format(str(oclc_num))
        _, ssh_stdout, _ = ssh.exec_command('curl "{}"'.format(url))
        data = json.loads(ssh_stdout.read())
        fullrecord = data['response']['docs'][0]['fullrecord']
    
        with io.BytesIO(fullrecord.encode('utf-8')) as fh:
            reader = MARCReader(fh)
            for record in reader:
                print_record = record

        identifier = digital_record['856']['u'].split('/').pop()
        tiff_path = '/'.join([
            '',
            'data',
            'digital_collections',
            'IIIF',
            'IIIF_Files',
            'maps',
            'chisoc',
            identifier,
            'tifs',
            '{0}.tif'.format(identifier)
        ])

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
            sha256 = hashlib.sha256(tiff_contents).hexdigest()

        edm = SocSciMapsMarcXmlToEDM(
            digital_record,
            print_record,
            [{
                'height': height,
                'md5': md5,
                'mime_type': mime_type,
                'name': '{}.tif'.format(identifier),
                'path': tiff_path,
                'sha256': sha256,
                'size': size,
                'width': width
            }]
        )

        edm.build_item_triples()

    if options['--socscimaps-project-triples']:
        SocSciMapsMarcXmlToEDM.build_repository_triples()
        SocSciMapsMarcXmlToEDM.build_digital_collections_triples()
        SocSciMapsMarcXmlToEDM.build_map_collection_triples()
        SocSciMapsMarcXmlToEDM.build_socscimap_collection_triples()

        
    sys.stdout.write(SocSciMapsMarcXmlToEDM.triples())

if __name__ == "__main__":
    main()
