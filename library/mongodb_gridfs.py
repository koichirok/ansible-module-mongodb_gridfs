#!/usr/bin/python

# (c) 2018, KIKUCHI Koichiro <koichiro@hataki.jp>
#
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


#ANSIBLE_METADATA = {'metadata_version': '1.1',
#                    'status': ['preview'],
#                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: mongodb_gridfs
short_description: Puts or deletes a file from a MongoDB GridFS.
description:
    - Puts or deletes a file from a MongoDB GridFS.
options:
    login_user:
        description:
            - The username used to authenticate with
    login_password:
        description:
            - The password used to authenticate with
    login_host:
        description:
            - The host running the database
        default: localhost
    login_port:
        description:
            - The port to connect to
        default: 27017
    login_database:
        description:
            - The database where login credentials are stored
        default: database which specified by database option
    replica_set:
        description:
            - Replica set to connect to (automatically connects to primary for writes)
    database:
        description:
            - The name of the database to put/delete the file from
        required: true
    collection:
        description:
            - The name of the root collection to put/delete the file from
        default: fs
    src:
        description:
            - Local path to a file to put to the GridFS.
    content:
        description:
            - When used instead of `src', sets the contents of a file to the specified value.
    dest:
        description:
            - The path on the GridFS to put or delete
    replase:
        description:
            - remove other files with same name after put.
        default: false
    ssl:
        description:
            - Whether to use an SSL connection when connecting to the database
    ssl_cert_reqs:
        description:
            - Specifies whether a certificate is required from the other side of the connection, and whether it will be validated if provided.
        default: "CERT_REQUIRED"
        choices: ["CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"]
    state:
        description:
            - Whether to add (`present'), or remove (`absent') a file.
        default: present
        choices: [ "present", "absent" ]

notes:
    - THIS MODULE IS HIGHLY EXPERIMENTAL, NOT TESTED AND DOCUMENTED WELL
    - Requires the pymongo Python package on the remote host, version 2.4.2+. This
      can be installed using pip or the OS package manager. @see http://api.mongodb.org/python/current/installation.html
requirements: [ "pymongo" ]
author:
    - "KIKUCHI Koichiro (@koichirok)"
'''

EXAMPLES = '''
- name: example put file to GridFS
  copy:
    database: login
    src: /srv/myfiles/foo.conf
    dest: /etc/foo.conf

'''

#RETURN = '''
#'''

import os
import ssl as ssl_lib
import traceback
import hashlib
from distutils.version import LooseVersion

try:
    from pymongo import version as PyMongoVersion
    from pymongo import MongoClient
    import gridfs
except ImportError:
    try:  # for older PyMongo 2.2
        from pymongo import Connection as MongoClient
    except ImportError:
        pymongo_found = False
    else:
        pymongo_found = True
else:
    pymongo_found = True

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native


# =========================================
# MongoDB module specific support methods.
#

def check_compatibility(module, client):
    """Check the compatibility between the driver and the database.

       See: https://docs.mongodb.com/ecosystem/drivers/driver-compatibility-reference/#python-driver-compatibility

    Args:
        module: Ansible module.
        client (cursor): Mongodb cursor on admin database.
    """
    loose_srv_version = LooseVersion(client.server_info()['version'])
    loose_driver_version = LooseVersion(PyMongoVersion)

    if loose_srv_version >= LooseVersion('3.2') and loose_driver_version < LooseVersion('3.2'):
        module.fail_json(msg=' (Note: you must use pymongo 3.2+ with MongoDB >= 3.2)')

    elif loose_srv_version >= LooseVersion('3.0') and loose_driver_version <= LooseVersion('2.8'):
        module.fail_json(msg=' (Note: you must use pymongo 2.8+ with MongoDB 3.0)')

    elif loose_srv_version >= LooseVersion('2.6') and loose_driver_version <= LooseVersion('2.7'):
        module.fail_json(msg=' (Note: you must use pymongo 2.7+ with MongoDB 2.6)')

    elif LooseVersion(PyMongoVersion) <= LooseVersion('2.5'):
        module.fail_json(msg=' (Note: you must be on mongodb 2.4+ and pymongo 2.5+ to use the roles param)')


def load_mongocnf():
    config = configparser.RawConfigParser()
    mongocnf = os.path.expanduser('~/.mongodb.cnf')

    try:
        config.readfp(open(mongocnf))
        creds = dict(
            user=config.get('client', 'user'),
            password=config.get('client', 'pass')
        )
    except (configparser.NoOptionError, IOError):
        return False

    return creds


def connect(params):
    login_user = params['login_user']
    login_password = params['login_password']
    login_host = params['login_host']
    login_port = params['login_port']
    login_database = params['login_database']
    replica_set = params['replica_set']
    db_name = params['database']
    collection = params['collection']
    ssl = params['ssl']

    if login_database is None:
        login_database = db_name

    connection_params = {
        "host": login_host,
        "port": int(login_port),
    }

    if replica_set:
        connection_params["replicaset"] = replica_set

    if ssl:
        connection_params["ssl"] = ssl
        connection_params["ssl_cert_reqs"] = getattr(ssl_lib, module.params['ssl_cert_reqs'])

    client = MongoClient(**connection_params)

    # NOTE: this check must be done ASAP.
    # We doesn't need to be authenticated (this ability has lost in PyMongo 3.6)
    if LooseVersion(PyMongoVersion) <= LooseVersion('3.5'):
        check_compatibility(module, client)

    if login_user is None and login_password is None:
        mongocnf_creds = load_mongocnf()
        if mongocnf_creds is not False:
            login_user = mongocnf_creds['user']
            login_password = mongocnf_creds['password']
    elif login_password is None or login_user is None:
        module.fail_json(msg='when supplying login arguments, both login_user and login_password must be provided')

    if login_user is not None and login_password is not None:
        if login_database is None:
            login_database = db_name
        client.admin.authenticate(login_user, login_password, source=login_database)

    db = client[db_name]

    return gridfs.GridFS(db, collection)


def delete_all(fs, filename, exclude=None):
    for grid_out in fs.find({'filename': filename}):
        if grid_out._id != exclude:
            fs.delete(grid_out._id)

def md5(content):
    m = hashlib.md5()
    m.update(content)

    return m.hexdigest()


# =========================================
# Module execution.
#

def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(default=None),
            login_password=dict(default=None, no_log=True),
            login_host=dict(default='localhost'),
            login_port=dict(default='27017'),
            login_database=dict(default=None),
            replica_set=dict(default=None),
            database=dict(required=True, aliases=['db']),
            ssl=dict(default=False, type='bool'),
            ssl_cert_reqs=dict(default='CERT_REQUIRED', choices=['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']),
            collection=dict(default='fs'),
            src=dict(type='path'),
            content=dict(type='str'),
            replace=dict(default=False, type='bool'),
            dest=dict(type='path', required=True),
            state=dict(default='present', choices=['absent', 'present']),
        ),
        required_if=[
            ('state', 'present', ['content','src'], True),
        ],
        mutually_exclusive=[('content', 'src')],
        supports_check_mode=True
    )

    if not pymongo_found:
        module.fail_json(msg='the python pymongo module is required')

    filename = module.params['dest']
    content = module.params['content']
    state = module.params['state']
    replace = module.params['replace']

    try:
        fs = connect(module.params)
    except Exception as e:
        module.fail_json(msg='unable to connect to database: %s' % to_native(e), exception=traceback.format_exc())

    try:
        if fs.exists({"filename": filename}):
            last_version = fs.get_last_version(filename)
            last_content = last_version.read()
            last_content_md5 = last_version.md5
        else:
            last_version = None
            last_content = ""
            last_content_md5 = md5("")

        if module.check_mode and module._diff:
            diff = {
                'before_header': filename,
                'after_header': filename,
                'before': last_content,
                'after': content if state == 'present' else '',
            }
        else:
            diff = {}

        if state == 'absent':
            change_required = last_version is not None
            if module.check_mode:
                module.exit_json(changed=change_required, diff=diff)
            if change_required:
                delete_all(fs, filename)
                module.exit_json(changed=True)
            module.exit_json(changed=False)
        elif state == 'present':
            change_required = last_content_md5 != md5(content)
            if module.check_mode:
                module.exit_json(changed=change_required, diff=diff)
            if change_required:
                _id = fs.put(content, filename=filename)
                if replace:
                    delete_all(fs, filename, _id)
            module.exit_json(changed=change_required)

        module.exit_json(changed=True)
    except Exception as e:
        module.fail_json(msg='Exception occurred durgin gridfs operation: %s' % to_native(e), exception=traceback.format_exc())


if __name__ == '__main__':
    main()
