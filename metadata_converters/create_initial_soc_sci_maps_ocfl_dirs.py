import json, os, re, shutil, subprocess
import xml.etree.ElementTree as ET
from marc2edm import marc_to_edm_soc_sci
from marc2dc import marc_to_dc_soc_sci

digital_records = ['11435664', '11435665', '11435666', '11435667',
'11435668', '11435669', '11435670', '11435671', '11435672', '11435673',
'11435674', '11435675', '11435676', '11435677', '11435678', '11435679',
'1582888', '1582891', '1582893', '1586198', '1586219', '3401134',
'3404181', '3450640', '3450644', '39315', '5043062', '5043187',
'5043398', '5043675', '5043919', '5059056', '5063149', '5063673',
'5063697', '5063699', '5063706', '5070204', '5077687', '5570199',
'5998122', '5999564', '5999565', '5999566', '7641168']

noids = ['b2gg00s0zd88', 'b2gg6296r847', 'b2h505p2k84p',
'b2hb1dc9ft8j', 'b2hr8g07j491', 'b2jf2bv76x74', 'b2jk7b25458m',
'b2k04f36mh8s', 'b2k172z1q79c', 'b2k57z87tt0h', 'b2k86bv2x025',
'b2kg6jc3941j', 'b2kr7zh82s5j', 'b2kx1qx1n50w', 'b2mk7qv7h276',
'b2mm3nk1mj7d', 'b2mp4j580m13', 'b2mx21f2x54x', 'b2mz7z92wv8n',
'b2n28w299w1k', 'b2nd42r7xp0q', 'b2nn6x21dq59', 'b2nw3wm8552h',
'b2nz6kd3rj2p', 'b2pn1qx6zj2t', 'b2q41s96rb7w', 'b2q573m8n49d',
'b2q84g22958x', 'b2qd0bb4kk01', 'b2qn59n7fr6d', 'b2qr3b65cv85',
'b2qv8nq0bz3c', 'b2qz5pj08k60', 'b2rd94h3tn54', 'b2rg9v099q4f',
'b2s05v615c5v', 'b2sc7207dq18', 'b2st63w23x7j', 'b2tf4wj2mp94',
'b2tp7h191k7k', 'b2v29bx9gj8v', 'b2vm2sg8j85v', 'b2w23nh6678g',
'b2w27c162t47', 'b2w80rn9bb9v']

orig_data_directory = '/data/digital_collections/IIIF/IIIF_Files/maps/chisoc'
tmp_dir = '/tmp/metadata_converters'

subdirs = {}
for subdir in os.listdir(orig_data_directory):
    with open('{0}/{1}/{1}.xml'.format(orig_data_directory, subdir)) as f:
        xml = ET.parse(f)
        for element in xml.find('{http://www.loc.gov/MARC21/slim}record').findall('{http://www.loc.gov/MARC21/slim}controlfield'):
            if element.attrib['tag'] == '001':
                subdirs[element.text] = subdir

for i, d in enumerate(digital_records):
    pair_tree_directory = '/data/digital_collections/{}'.format(
        os.sep.join([noids[i][c:c+2] for c in range(0, len(noids[i]), 2)])
    )
    pair_tree_directory_parent = os.path.abspath(os.path.join(pair_tree_directory, os.pardir))
    pair_tree_directory_leaf = os.path.basename(os.path.normpath(pair_tree_directory))

    # make pair tree directory.
    if not os.path.exists(pair_tree_directory_parent):
        os.makedirs(pair_tree_directory_parent)

    # make temporary directory.
    if not os.path.exists('{}/{}'.format(tmp_dir, pair_tree_directory_leaf)):
        os.makedirs('{}/{}'.format(tmp_dir, pair_tree_directory_leaf))

    # file.xml
    shutil.copyfile(
        '{0}/{1}/{1}.xml'.format(orig_data_directory, subdirs[d]),
        '{}/{}/file.xml'.format(tmp_dir, pair_tree_directory_leaf)
    )

    # file.tif
    shutil.copyfile(
        '{0}/{1}/tifs/{1}.tif'.format(orig_data_directory, subdirs[d]),
        '{}/{}/file.tif'.format(tmp_dir, pair_tree_directory_leaf)
    )

    # file.dc.xml
    with open('{}/{}/file.dc.xml'.format(tmp_dir, pair_tree_directory_leaf), 'w') as f:
        f.write(
            marc_to_dc_soc_sci(
                d,
                noids[i]
            )
        )

    # file.ttl
    with open('{}/{}/file.ttl'.format(tmp_dir, pair_tree_directory_leaf), 'w') as f:
        f.write(
            marc_to_edm_soc_sci(
                False,
                '{}/{}/tifs'.format(orig_data_directory, subdirs[d]),
                d,
                noids[i]
            )
        )

    inventory_str = subprocess.run([
        'ocfl-object.py',
        '--create',
        '--srcdir',
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf),
        '--id',
        'ark:/61001/{}'.format(noids[i]),
        '--message', 
        'Initial commit.',
        '--name',
        'John Jung',
        '--address',
        'mailto:jej@uchicago.edu'
    ], stderr=subprocess.PIPE).stderr.decode('utf-8')
    # remove WARNING line.
    inventory_str = re.sub('^WARNING.*', '', inventory_str)
    # remove additional space and pretty print. 
    inventory_str = json.dumps(json.loads(inventory_str), indent=4)
    # write it.
    with open('{}/{}/inventory.json'.format(tmp_dir, pair_tree_directory_leaf), 'w') as f:
        f.write(inventory_str)

    # create sidecar. 
    subprocess.run([
        'ocfl-sidecar.py',
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf)
    ])

    # create version directories. 
    if not os.path.exists('{}/{}/v1/content'.format(tmp_dir, pair_tree_directory_leaf)):
        os.makedirs('{}/{}/v1/content'.format(tmp_dir, pair_tree_directory_leaf))

    # move files into v1 directory.
    for fname in ('file.dc.xml', 'file.tif', 'file.ttl', 'file.xml'):
        shutil.move(
            '{}/{}/{}'.format(tmp_dir, pair_tree_directory_leaf, fname),
            '{}/{}/v1/content/'.format(tmp_dir, pair_tree_directory_leaf)
        )

    # copy the inventory and sidecar into v1.
    for fname in ('inventory.json', 'inventory.json.sha512'):
        shutil.copy(
            '{}/{}/{}'.format(tmp_dir, pair_tree_directory_leaf, fname),
            '{}/{}/v1/'.format(tmp_dir, pair_tree_directory_leaf)
        )

    # create a namaste file.
    with open('{}/{}/0=ocfl_object_1.0'.format(tmp_dir, pair_tree_directory_leaf), 'w') as f:
        f.write('ocfl_object_1.0')

    # move this directory into place in the pair tree.
    shutil.move(
        '{}/{}'.format(tmp_dir, pair_tree_directory_leaf),
        pair_tree_directory_parent
    )
