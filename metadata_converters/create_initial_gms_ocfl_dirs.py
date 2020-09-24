import json, os, re, requests, shutil, sqlite3, subprocess, sys
import xml.etree.ElementTree as ET
from classes import NoidManager

conn = sqlite3.connect('/data/s4/jej/ark_data.db')
c = conn.cursor()

orig_data_directory = '/data/digital_collections/IIIF/IIIF_Files/gms'
tmp_dir = '/tmp/metadata_converters/gms'
ark_data = '/data/digital_collections/ark_data'

nm = NoidManager(ark_data)

for d in os.listdir(orig_data_directory):
    if d != 'gms-0125':
        continue

    # clear out the temp directory.
    '''
    subprocess.run([
        'rm',
        '-rdf',
        tmp_dir
    ])
    '''

    # get original identifier.
    original_identifier = d

    noid = nm.create()
    ark = 'ark:61001/{}'.format(noid)
    print(ark)

    pair_tree_directory = '{}/{}'.format(
        ark_data,
        os.sep.join([noid[c:c+2] for c in range(0, len(noid), 2)])
    )
    pair_tree_directory_parent = os.path.abspath(os.path.join(pair_tree_directory, os.pardir))
    pair_tree_directory_leaf = os.path.basename(os.path.normpath(pair_tree_directory))

    # make temporary directory.
    '''
    if not os.path.exists('{}/tmp'.format(tmp_dir)):
        os.makedirs('{}/tmp'.format(tmp_dir))
    '''

    # tifs
    '''
    tiffs = []
    for tiff in os.listdir('{}/{}/tifs'.format(orig_data_directory, d)):
        if re.match('^gms-[0-9]{4}-[0-9]{3}\.tif$', tiff) == None:
            print('FILE NAMING ERROR')
        tiffs.append(tiff)
    tiffs.sort()
    '''

    '''
    for tiff in tiffs:
        image_identifier = '00000{}'.format(tiff.split('-')[2].split('.')[0])
        os.makedirs('{}/tmp/{}'.format(tmp_dir, image_identifier))

        shutil.copyfile(
            '{}/{}/tifs/{}'.format(orig_data_directory, d, tiff),
            '{}/tmp/{}/file.tif'.format(tmp_dir, image_identifier)
        )
    '''

    # file.dc.xml
    '''
    with open('{}/tmp/file.dc.xml'.format(tmp_dir), 'w') as f:
        f.write(
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier>{}</dc:identifier></metadata>'.format(d)
        )
    '''

    subprocess.run([
        'ocfl-object.py',
        '--create',
        '--srcdir',
        '{}/tmp'.format(tmp_dir),
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

    # make pair tree directory.
    if not os.path.exists(pair_tree_directory_parent):
        os.makedirs(pair_tree_directory_parent)

    # move this directory into place in the pair tree.
    shutil.move(
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf),
        pair_tree_directory_parent
    )

    # update the database.
    c.execute('INSERT INTO arks VALUES (?, ?, ?)', ('goodspeed', ark, original_identifier))
    conn.commit()
