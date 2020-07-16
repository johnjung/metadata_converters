#!/usr/bin/env python
"""Usage:
    marc2dc --socscimaps <digital_record_id> --noid <noid>
"""

import io, json, os, paramiko, sys
import xml.etree.ElementTree as ElementTree

from classes import SocSciMapsMarcXmlToDc
from docopt import docopt
from pymarc import MARCReader

ElementTree.register_namespace('m', 'http://www.loc.gov/MARC21/slim')

def marc_to_dc_soc_sci(digital_record_id, noid):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        os.environ['SOLR_ACCESS_DOMAIN'],
        username=os.environ['SOLR_ACCESS_USERNAME'],
        password=os.environ['SOLR_ACCESS_PASSWORD']
    )

    # request the digital record
    url = 'http://vfsolr.uchicago.edu:8080/solr/biblio/select?q=id:{}'.format(str(digital_record_id))
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

    return str(SocSciMapsMarcXmlToDc(digital_record, print_record, noid))

if __name__ == "__main__":
    options = docopt(__doc__)
    sys.stdout.write(
        marc_to_dc_soc_sci(
            options['<digital_record_id>'],
            options['<noid>']
        )
    )
