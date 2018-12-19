# mongodb_gridfs-module - Ansible mongodb_gridfs module

Puts or deletes a file from a MongoDB GridFS.

## Requirements

* PyMongo package

## Install

```
$ ansible-galaxy install koichirok.mongodb_gridfs-module
```

## Synopsis
 Puts or deletes a file from a MongoDB GridFS.

## Options

| Parameter     | required    | default  | choices    | comments |
| ------------- |-------------| ---------|----------- |--------- |
| login_port  |   |  27017  | |  The port to connect to  |
| database  |   yes  |  | |  The name of the database to put/delete the file from  |
| dest  |   |  | |  The path on the GridFS to put or delete  |
| login_user  |   |  | |  The username used to authenticate with  |
| login_host  |   |  localhost  | |  The host running the database  |
| login_password  |   |  | |  The password used to authenticate with  |
| ssl_cert_reqs  |   |  CERT_REQUIRED  | <ul> <li>CERT_REQUIRED</li>  <li>CERT_OPTIONAL</li>  <li>CERT_NONE</li> </ul> |  Specifies whether a certificate is required from the other side of the connection, and whether it will be validated if provided.  |
| collection  |   |  fs  | |  The name of the root collection to put/delete the file from  |
| content  |   |  | |  When used instead of `src', sets the contents of a file to the specified value.  |
| ssl  |   |  | |  Whether to use an SSL connection when connecting to the database  |
| state  |   |  present  | <ul> <li>present</li>  <li>absent</li> </ul> |  Whether to add (`present'), or remove (`absent')  |
| login_database  |   |  database which specified by database option  | |  The database where login credentials are stored  |
| src  |   |  | |  Local path to a file to put to the GridFS.  |
| replica_set  |   |  | |  Replica set to connect to (automatically connects to primary for writes)  |
| replase  |   |  False  | |  remove other files with same name after put.  |


## Examples

```

- name: example put file to GridFS
  copy:
    database: login
    src: /srv/myfiles/foo.conf
    dest: /etc/foo.conf


```

## Return Values

## Notes

- THIS MODULE IS HIGHLY EXPERIMENTAL, NOT TESTED AND DOCUMENTED WELL

- Requires the pymongo Python package on the remote host, version 2.4.2+. This can be installed using pip or the OS package manager. @see http://api.mongodb.org/python/current/installation.html

## License

GPLv3
