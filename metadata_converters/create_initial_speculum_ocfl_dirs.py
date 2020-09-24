import json, os, re, requests, shutil, sqlite3, subprocess, sys
import xml.etree.ElementTree as ET
from classes import NoidManager
from marc2edm import marc_to_edm_soc_sci
from marc2dc import marc_to_dc_soc_sci

speculum_ids_present = set()
conn = sqlite3.connect('/data/s4/jej/ark_data.db')
c = conn.cursor()
c.execute('SELECT ark from arks where project="speculum"')
results = c.fetchall()
for result in results:
    ark = result[0]
    request = requests.get('https://ark.lib.uchicago.edu/{}/file.dc.xml'.format(ark))
    m = re.search('speculum-[0-9]{4}', request.text)
    speculum_ids_present.add(m.group(0))

# there are 994 speculum directories, numbered speculum-0001 to
# speculum-0994.

orig_data_directory = '/data/digital_collections/IIIF/IIIF_Files/speculum'
tmp_dir = '/tmp/metadata_converters'
ark_data = '/data/digital_collections/ark_data'

nm = NoidManager(ark_data)

for d in os.listdir(orig_data_directory):
    # only work with directories that match the following regex:
    if not re.match('^speculum-[0-9]{4}$', d):
        continue

    # skip 0625, 0647, 0652
    if not os.path.exists('{0}/{1}/tifs/{1}-001.tif'.format(orig_data_directory, d)):
        continue

    # skip anything that is already in the database.
    if d in speculum_ids_present:
        continue

    # clear out the temp directory.
    subprocess.run([
        'rm',
        '-rdf',
        tmp_dir
    ])

    noid = nm.create()
    print('ark:61001/{}'.format(noid))

    pair_tree_directory = '{}/{}'.format(
        ark_data,
        os.sep.join([noid[c:c+2] for c in range(0, len(noid), 2)])
    )
    pair_tree_directory_parent = os.path.abspath(os.path.join(pair_tree_directory, os.pardir))
    pair_tree_directory_leaf = os.path.basename(os.path.normpath(pair_tree_directory))

    # make pair tree directory.
    if not os.path.exists(pair_tree_directory_parent):
        os.makedirs(pair_tree_directory_parent)

    # make temporary directory.
    if not os.path.exists('{}/speculum'.format(tmp_dir)):
        os.makedirs('{}/speculum'.format(tmp_dir))

    # file.tif
    shutil.copyfile(
        '{0}/{1}/tifs/{1}-001.tif'.format(orig_data_directory, d),
        '{}/speculum/file.tif'.format(tmp_dir)
    )

    # file.dc.xml
    with open('{}/speculum/file.dc.xml'.format(tmp_dir), 'w') as f:
        f.write(
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier>{}</dc:identifier></metadata>'.format(d)
        )

    subprocess.run([
        'ocfl-object.py',
        '--create',
        '--srcdir',
        '{}/speculum'.format(tmp_dir),
        '--id',
        'ark:61001/{}'.format(noid),
        '--message', 
        'Initial commit.',
        '--name',
        'John Jung',
        '--address',
        'mailto:jej@uchicago.edu',
        '--objdir',
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf)
    ])

    # move this directory into place in the pair tree.
    shutil.move(
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf),
        pair_tree_directory_parent
    )
