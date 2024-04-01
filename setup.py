#!/usr/bin/env python3
#
import sys
import argparse
import subprocess
import base64
import socket, struct
import pwd
import grp
import time
import inspect
import os
from urllib.request import urlretrieve
import shutil
import requests
import random
import json
import pathlib

verbosity = None
def run():
    global verbosity
    description = 'Configure TON full node or dht server'
    parser = argparse.ArgumentParser(formatter_class = argparse.RawDescriptionHelpFormatter,
                                     description = description)

    parser.add_argument('-m', '--mode',
                        required=True,
                        type=str,
                        dest='mode',
                        action='store',
                        help='[node|dht] - REQUIRED')

    parser.add_argument('-I', '--instance-name',
                        required=True,
                        type=str,
                        dest='instance_name',
                        action='store',
                        help='Instance name, will be used for service naming - REQUIRED')

    parser.add_argument('-d', '--dist-home',
                        required=True,
                        type=str,
                        dest='dist_home',
                        action='store',
                        help='TON Distribution home / basepath (path which was specified during cmake install step) - REQUIRED')

    parser.add_argument('-g', '--global-config',
                        required=True,
                        type=str,
                        dest='global_config',
                        action='store',
                        help='URL of file to network global config - REQUIRED')

    parser.add_argument('-H', '--home',
                        required=True,
                        type=str,
                        dest='home',
                        action='store',
                        help='Home of node / server - REQUIRED')

    parser.add_argument('--etc-path',
                        required=False,
                        type=str,
                        dest='etc_path',
                        action='store',
                        help='Path to store configs and keys needed to access node / service - OPTIONAL, defaults to $HOME/etc')

    parser.add_argument('--db-path',
                        required=False,
                        type=str,
                        dest='db_path',
                        action='store',
                        help='Path to service database - OPTIONAL, defaults to $HOME/db')

    parser.add_argument('--log-path',
                        required=False,
                        type=str,
                        dest='log_path',
                        action='store',
                        help='Path to logs - OPTIONAL, defaults to $HOME/log')

    parser.add_argument('--backup-path',
                        required=False,
                        type=str,
                        dest='backup_path',
                        action='store',
                        help='Path to configuration backup - OPTIONAL, defaults to $HOME/backup')

    parser.add_argument('--restore-dump',
                        required=False,
                        type=str,
                        dest='dump_url',
                        action='store',
                        help='URL to node database dump in tar(!) format compressed with lzip - OPTIONAL')

    parser.add_argument('--address',
                        required=False,
                        type=str,
                        dest='address',
                        action='store',
                        help='Public IP address of machine, if not specified will attempt to detect using http://checkip.amazonaws.com - OPTIONAL')

    parser.add_argument('--service-port',
                        required=False,
                        type=str,
                        dest='service_port',
                        action='store',
                        help='Main UDP port of full node / dht server - OPTIONAL')

    parser.add_argument('--ls-port',
                        required=False,
                        type=str,
                        dest='ls_port',
                        action='store',
                        help='Liteserver port - OPTIONAL')

    parser.add_argument('--console-port',
                        required=False,
                        type=str,
                        dest='console_port',
                        action='store',
                        help='Node console port - OPTIONAL')

    parser.add_argument('--sync-before',
                        required=False,
                        type=int,
                        default=604800,
                        dest='sync_before',
                        action='store',
                        help='History to sync on new node - OPTIONAL, defaults to 604800')

    parser.add_argument('--install-user',
                        required=False,
                        type=str,
                        dest='install_user',
                        action='store',
                        help='Set username to own directories - OPTIONAL, defaults to current user')

    parser.add_argument('--service-user',
                        required=False,
                        type=str,
                        dest='service_user',
                        action='store',
                        help='Set username to run service - OPTIONAL, defaults to current user')

    parser.add_argument('--state-ttl',
                        required=False,
                        type=int,
                        default=604800,
                        dest='state_ttl',
                        action='store',
                        help='Set state ttl value to specified number of seconds - OPTIONAL, defaults to 604800')

    parser.add_argument('--archive-ttl',
                        required=False,
                        type=int,
                        default=86400,
                        dest='archive_ttl',
                        action='store',
                        help='Set archive ttl value to specified number of seconds - OPTIONAL, defaults to 86400')

    parser.add_argument('--service-verbosity',
                        required=False,
                        type=int,
                        default=1,
                        dest='service_verbosity',
                        action='store',
                        help='Set service verbosity to specified value - OPTIONAL, defaults to 1')

    parser.add_argument('--service-threads',
                        required=False,
                        type=int,
                        default=os.cpu_count()-1,
                        dest='service_threads',
                        action='store',
                        help='Set service threads to specified value - OPTIONAL, defaults to number of cores -1')

    parser.add_argument('--use-cronolog',
                        required=False,
                        dest='use_cronolog',
                        action='store_true',
                        help='Use cronolog to rotate logs - OPTIONAL')

    parser.add_argument('--cronolog-bin',
                        required=False,
                        type=str,
                        dest='cronolog_bin',
                        action='store',
                        help='Cronolog binary - OPTIONAL')

    parser.add_argument('--cronolog-template',
                        required=False,
                        type=str,
                        default='%%Y-%%m-%%d.log',
                        dest='cronolog_template',
                        action='store',
                        help='Template for cronolog filename - OPTIONAL, defaults to %%Y-%%m-%%d.log')

    parser.add_argument('--force',
                        required=False,
                        dest='force',
                        action='store_true',
                        help='Destroy / overwrite existing configuration and db - OPTIONAL and DANGEROUS')

    parser.add_argument('--install-systemd-service',
                        required=False,
                        dest='install_systemd_service',
                        action='store_true',
                        help='Install service - OPTIONAL')

    parser.add_argument('--start-systemd-service',
                        required=False,
                        dest='start_systemd_service',
                        action='store_true',
                        help='Start service - OPTIONAL')

    parser.add_argument('-v', '--verbosity',
                        required=False,
                        type=int,
                        dest='verbosity',
                        action='store',
                        default=3,
                        help='Verbosity for this script - OPTIONAL')

    args = parser.parse_args()
    verbosity = args.verbosity

    log(inspect.currentframe().f_code.co_name, 3, "Checking parameters")
    if not os.path.exists(args.dist_home):
        log(inspect.currentframe().f_code.co_name, 1, "Distribution path {} does not exist".format(args.dist_home))
        sys.exit(1)
    elif args.use_cronolog and args.cronolog_bin and not os.path.isfile(args.cronolog_bin):
        log(inspect.currentframe().f_code.co_name, 1, "Cronolog binary {} does not exist").format(args.cronolog_bin)
        sys.exit(1)
    elif args.use_cronolog and not args.cronolog_bin and not shutil.which('cronolog'):
        log(inspect.currentframe().f_code.co_name, 1, "Cronolog binary file cannot be found")
        sys.exit(1)
    elif args.mode not in ('node', 'dht'):
        log(inspect.currentframe().f_code.co_name, 1, "Unknown mode '{}'".format(args.mode))
        sys.exit(1)

    log(inspect.currentframe().f_code.co_name, 3, "Populating instance data")
    instance_data = {
        'name': args.instance_name,
        'mode': args.mode,
        'network': {
            'address': None,
            'service_port': None,
            'ls_port': None,
            'console_port': None
        },
        'paths': {
            'dist': args.dist_home.rstrip('/'),
            'home': args.home.rstrip('/'),
            'etc': None,
            'db': None,
            'log': None,
            'backup': None
        },
        'configs': {
            'node': None,
            'global': None
        },
        'keys': {},
        'setup_params': vars(args),
        'binaries': {
            'process': None,
            'validator_engine_console': "{}/bin/validator-engine-console".format(args.dist_home.rstrip('/')),
            'generate_random_id': "{}/bin/generate-random-id".format(args.dist_home.rstrip('/')),
            'sed': shutil.which('sed'),
            'cronolog': shutil.which('cronolog')
        },
        'users': {
            'install': {
                'user': None,
                'uid': None,
                'group': None,
                'gid': None
            },
            'service': {
                'user': None,
                'uid': None,
                'group': None,
                'gid': None
            }
        }
    }

    if args.etc_path:
        instance_data['paths']['etc'] = args.etc_path.rstrip('/')
    else:
        instance_data['paths']['etc'] = '{}/etc'.format(instance_data['paths']['home'])

    if args.db_path:
        instance_data['paths']['db'] = args.db_path.rstrip('/')
    else:
        instance_data['paths']['db'] = '{}/db'.format(instance_data['paths']['home'])

    if args.log_path:
        instance_data['paths']['log'] = args.log_path.rstrip('/')
    else:
        instance_data['paths']['log'] = '{}/logs'.format(instance_data['paths']['home'])

    instance_data['paths']['init_log'] = '{}/init'.format(instance_data['paths']['log'])

    if args.backup_path:
        instance_data['paths']['backup'] = args.backup_path.rstrip('/')
    else:
        instance_data['paths']['backup'] = '{}/backups'.format(instance_data['paths']['home'])

    if args.address:
        instance_data['network']['address'] = args.address
    else:
        instance_data['network']['address'] = requests.get('http://checkip.amazonaws.com', allow_redirects=True).text.strip()

    if args.install_user:
        instance_data['users']['install']['user'] = args.install_user
    else:
        instance_data['users']['install']['user'] = os.environ.get('USER')

    if args.service_user:
        instance_data['users']['service']['user'] = args.service_user
    else:
        instance_data['users']['service']['user'] = os.environ.get('USER')

    if args.mode == 'node':
        instance_data['binaries']['process'] = "{}/bin/validator-engine".format(instance_data['paths']['dist'])
    elif args.mode == 'dht':
        instance_data['binaries']['process'] = "{}/bin/dht-server".format(instance_data['paths']['dist'])

    elif not os.path.isfile(instance_data['binaries']['process']):
        log(inspect.currentframe().f_code.co_name, 1, "Process binary {} does not exist".format(instance_data['binaries']['process']))
        sys.exit(1)

    user_data = pwd.getpwnam(instance_data['users']['install']['user'])
    group_data = grp.getgrgid(user_data.pw_gid)
    instance_data['users']['install']['uid'] = user_data.pw_uid
    instance_data['users']['install']['gid'] = user_data.pw_gid
    instance_data['users']['install']['group'] = group_data.gr_name

    user_data = pwd.getpwnam(instance_data['users']['service']['user'])
    group_data = grp.getgrgid(user_data.pw_gid)
    instance_data['users']['service']['uid'] = user_data.pw_uid
    instance_data['users']['service']['gid'] = user_data.pw_gid
    instance_data['users']['service']['group'] = group_data.gr_name


    used_ports = []
    if args.service_port:
        instance_data['network']['service_port'] = args.service_port
    else:
        instance_data['network']['service_port'] = get_unused_port(used_ports)

    if args.mode == 'node':
        if args.ls_port:
            instance_data['network']['ls_port'] = args.ls_port
        else:
            instance_data['network']['ls_port'] = get_unused_port(used_ports)

        if args.console_port:
            instance_data['network']['console_port'] = args.console_port
        else:
            instance_data['network']['console_port'] = get_unused_port(used_ports)

    if args.cronolog_bin and os.path.isfile(args.cronolog_bin):
        instance_data['binaries']['cronolog'] = args.cronolog_bin

    instance_data['configs']['global'] = "{}/global.config.json".format(instance_data['paths']['etc'])
    instance_data['configs']['local'] = "{}/local.config.json".format(instance_data['paths']['etc'])
    instance_data['configs']['snip'] = "{}/snip.config.json".format(instance_data['paths']['etc'])
    instance_data['configs']['instance'] = "{}/instance.config.json".format(instance_data['paths']['etc'])
    instance_data['configs']['node'] = "{}/config.json".format(instance_data['paths']['db'])

    log(inspect.currentframe().f_code.co_name, 3, "Checking instance data")
    checkfile = '{}/config.json'.format(instance_data['paths']['db'])
    if os.path.isfile(checkfile):
        log(inspect.currentframe().f_code.co_name, 3, "Database config file {} already exists".format(checkfile))
        if not args.force:
            no_force_exit("Database exists")
        else:
            log(inspect.currentframe().f_code.co_name, 3, "Destroying database")
            shutil.rmtree(instance_data['paths']['db'])

    checkfile = "{}/keys".format(instance_data['paths']['etc'])
    if os.path.isdir(checkfile):
        log(inspect.currentframe().f_code.co_name, 3, "Keys directory {} already exists".format(checkfile))
        if not args.force:
            no_force_exit("Keys directory exists")
        else:
            log(inspect.currentframe().f_code.co_name, 3, "Destroying keys")
            shutil.rmtree(checkfile)

    checkfile = "{}/initial".format(instance_data['paths']['backup'])
    if os.path.isdir(checkfile):
        log(inspect.currentframe().f_code.co_name, 3, "Initial backups directory {} already exists".format(checkfile))
        if not args.force:
            no_force_exit("Initial backups directory exists")
        else:
            log(inspect.currentframe().f_code.co_name, 3, "Destroying initial backup")
            shutil.rmtree(checkfile)

    log(inspect.currentframe().f_code.co_name, 3, "Doing work")
    log(inspect.currentframe().f_code.co_name, 3, "Creating paths")
    create_paths(instance_data['paths'], args.force)

    if args.global_config.startswith('http'):
        log(inspect.currentframe().f_code.co_name, 3, "Fetching global config from {}".format(args.global_config))
        urlretrieve(args.global_config, instance_data['configs']['global'])
    elif os.path.isfile(args.global_config):
        log(inspect.currentframe().f_code.co_name, 3, "Copying global config from {}".format(args.global_config))
        shutil.copyfile(args.global_config, instance_data['configs']['global'])
    else:
        log(inspect.currentframe().f_code.co_name, 1, "Specified global config {} cannot be found".format(args.global_config))
        sys.exit(1)

    log(inspect.currentframe().f_code.co_name, 3, "Initializing database in {}".format(instance_data['paths']['db']))
    log_file = "{}/init".format(instance_data['paths']['init_log'])
    process_args = [instance_data['binaries']['process'],
                    "--global-config", instance_data['configs']['global'],
                    "--db", instance_data['paths']['db'],
                    "--ip", "{}:{}".format(instance_data['network']['address'],instance_data['network']['service_port']),
                    "--logname", log_file,
                    "--verbosity", "3"]

    try:
        process = subprocess.run(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=10)
        if process.returncode > 0:
            log(inspect.currentframe().f_code.co_name, 1, "Database initialization failed: {}".format(process.stderr.decode("utf-8")))
            sys.exit(1)
    except Exception as e:
        log(inspect.currentframe().f_code.co_name, 1, "Execution of process failed: {}".format(e))
        sys.exit(1)

    if args.mode == 'node':
        log(inspect.currentframe().f_code.co_name, 3, "Reading node configuration file {}".format(instance_data['configs']['node']))
        node_config = None
        with open(instance_data['configs']['node'], 'r') as fh:
            node_config = json.loads(fh.read())

        if not node_config:
            log(inspect.currentframe().f_code.co_name, 1, "Could not read node configuration")
            sys.exit(1)

        log(inspect.currentframe().f_code.co_name, 3, "Generating console server, client and liteserver keys")
        instance_data['keys']['server'] = mk_keys("{}/keys/server".format(instance_data['paths']['etc']), instance_data['paths']['dist'])
        instance_data['keys']['client'] = mk_keys("{}/keys/client".format(instance_data['paths']['etc']), instance_data['paths']['dist'])
        instance_data['keys']['liteserver'] = mk_keys("{}/keys/liteserver".format(instance_data['paths']['etc']), instance_data['paths']['dist'])

        log(inspect.currentframe().f_code.co_name, 3, "Moving private keys into node database")
        shutil.move("{}/keys/server".format(instance_data['paths']['etc']), "{}/keyring/{}".format(instance_data['paths']['db'], instance_data['keys']['server'][0]))
        shutil.move("{}/keys/liteserver".format(instance_data['paths']['etc']), "{}/keyring/{}".format(instance_data['paths']['db'], instance_data['keys']['liteserver'][0]))

        log(inspect.currentframe().f_code.co_name, 3, "Appending lite server configuration")
        node_config['liteservers'] = [
            {
                "@type": "engine.liteServer",
                "id": instance_data['keys']['liteserver'][1],
                "port" : instance_data['network']['ls_port']
            }
        ]

        log(inspect.currentframe().f_code.co_name, 3, "Appending console server configuration")
        node_config['control'] = [
            {
                "@type": "engine.controlInterface",
                "id" : instance_data['keys']['server'][1],
                "port" : instance_data['network']['console_port'],
                "allowed" : [
                    {
                        "@type": "engine.controlProcess",
                        "id" : instance_data['keys']['client'][1],
                        "permissions" : 15
                    }
                ]
            }
        ]

        log(inspect.currentframe().f_code.co_name, 3, "Writing altered node configuration")
        with open(instance_data['configs']['node'], 'w') as fh:
            fh.write(json.dumps(node_config, indent=4))

        log(inspect.currentframe().f_code.co_name, 3, "Creating local node snippet file")
        local_snip = {
                "ip": struct.unpack('>i',socket.inet_aton(instance_data['network']['address']))[0],
                "port": instance_data['network']['ls_port'],
                "id": {
                    "@type": "pub.ed25519",
                    "key": instance_data['keys']['liteserver'][2]
                }
            }
        with open(instance_data['configs']['snip'], 'w') as fh:
            fh.write(json.dumps(local_snip, indent=4))

        log(inspect.currentframe().f_code.co_name, 3, "Creating local node config file")
        with open(instance_data['configs']['global'], 'r') as fh:
            local_config = json.loads(fh.read())
            local_config['liteservers'] = [local_snip]

            with open(instance_data['configs']['local'], 'w') as fw:
                fw.write(json.dumps(local_config, indent=4))

        log(inspect.currentframe().f_code.co_name, 3, "Starting node....")
        process_args = [instance_data['binaries']['process']] + get_node_params(instance_data=instance_data, first_run=True)
        process = subprocess.Popen(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log(inspect.currentframe().f_code.co_name, 3, "Waiting 3 seconds..")
        time.sleep(3)

        log(inspect.currentframe().f_code.co_name, 3, "Checking node function")
        rs = vc_exec(
            console_bin=instance_data['binaries']['validator_engine_console'],
            server_address='127.0.0.1',
            server_port=instance_data['network']['console_port'],
            server_key="{}/keys/server.pub".format(instance_data['paths']['etc']),
            client_key="{}/keys/client".format(instance_data['paths']['etc']),
            cmd='gettime'
        )

        if not rs.index('received validator time'):
            log(inspect.currentframe().f_code.co_name, 1, "Node is not responding, something went wrong....")
            sys.exit(1)

        log(inspect.currentframe().f_code.co_name, 3, "Stopping node....")
        process.terminate()
    else:
        log(inspect.currentframe().f_code.co_name, 3, "Creating local dht snippet file")
        local_snip = {
            "@type": "adnl.addressList",
            "addrs": [
                {
                    "@type": "adnl.address.udp",
                    "ip": struct.unpack('>i',socket.inet_aton(instance_data['network']['address']))[0],
                    "port": instance_data['network']['service_port']
                }
            ],
            "version": 0,
            "reinit_date": 0,
            "priority": 0,
            "expire_at": 0
        }

        log(inspect.currentframe().f_code.co_name, 3, "Signing DHT record")
        process_args = [
            instance_data['binaries']['generate_random_id'],
            "-m", "dht",
            "-k", "{}/keyring/{}".format(
                instance_data['paths']['db'],
                os.listdir("{}/keyring".format(instance_data['paths']['db']))[0]
            ),
            "-a", json.dumps(local_snip)
        ]
        process = subprocess.run(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode > 0:
            log(inspect.currentframe().f_code.co_name, 1, "Record signature failed: {}".format(process.stderr.decode("utf-8")))
            sys.exit(1)
        else:
            local_snip = json.loads(process.stdout.decode("utf-8"))

        with open(instance_data['configs']['snip'], 'w') as fh:
            fh.write(json.dumps(local_snip, indent=4))

        log(inspect.currentframe().f_code.co_name, 3, "Creating local node config file")
        with open(instance_data['configs']['global'], 'r') as fh:
            local_config = json.loads(fh.read())
            local_config['dht'] = [local_snip]

            with open(instance_data['configs']['local'], 'w') as fw:
                fw.write(json.dumps(local_config, indent=4))

    log(inspect.currentframe().f_code.co_name, 3, "Creating systemd service file")
    with open('{}/templates/{}.systemd.service'.format(pathlib.Path(__file__).parent, instance_data['mode']), 'r') as fh:
        process_args = [instance_data['binaries']['process']] + get_node_params(instance_data=instance_data, first_run=True)
        execstart = " ".join(process_args).strip()
        if instance_data['setup_params']['use_cronolog']:
            execstart =  cronolize_cmd(instance_data, execstart)

        service = parse_template(
            template=fh.read(),
            stash={
                '##DESCRIPTION##': "{} service".format(instance_data['name']),
                '##USER##': instance_data['users']['service']['user'],
                '##GROUP##': instance_data['users']['service']['group'],
                '##EXECSTART##': execstart
            }
        )

        service_file = '{}/{}.systemd.service'.format(instance_data['paths']['etc'], instance_data['name'])
        with open(service_file, 'w') as fh:
            fh.write(service)

            if instance_data['setup_params']['install_systemd_service']:
                log(inspect.currentframe().f_code.co_name, 3, "Installing systemd service {}".format(instance_data['name']))
                shutil.copy(service_file, '/etc/systemd/system/{}.service'.format(instance_data['name']))
                subprocess.run(["systemctl", "daemon-reload"])

    log(inspect.currentframe().f_code.co_name, 3, "Creating instance configuration file")
    with open(instance_data['configs']['instance'], 'w') as fh:
        fh.write(json.dumps(instance_data, indent=4))

    log(inspect.currentframe().f_code.co_name, 3, "Set owner of installed files")
    chown(path=instance_data['paths']['home'],
             uid=instance_data['users']['install']['uid'],
             gid=instance_data['users']['install']['gid'],
             recursive=True)

    log(inspect.currentframe().f_code.co_name, 3, "Set owner of service files")
    chown(path=instance_data['paths']['db'],
             uid=instance_data['users']['service']['uid'],
             gid=instance_data['users']['service']['gid'],
             recursive=True)
    chown(path=instance_data['paths']['log'],
             uid=instance_data['users']['service']['uid'],
             gid=instance_data['users']['service']['gid'],
             recursive=True)

    log(inspect.currentframe().f_code.co_name, 3, "Creating configuration backup")
    shutil.copy("{}/config.json".format(instance_data['paths']['db']), "{}/initial".format(instance_data['paths']['backup']))
    shutil.copytree("{}/keyring".format(instance_data['paths']['db']), "{}/initial/keyring".format(instance_data['paths']['backup']))

    if instance_data['setup_params']['start_systemd_service']:
        log(inspect.currentframe().f_code.co_name, 3, "Enabling and starting systemd service {}".format(instance_data['name']))
        subprocess.run(["systemctl", "enable", instance_data['name']])
        subprocess.run(["systemctl", "start", instance_data['name']])

    log(inspect.currentframe().f_code.co_name, 3, "Work completed")

def cronolize_cmd(instance_data, cmd):
    return "/bin/sh -c '{} 2>&1 | {} -u -e \"s/\\x1b\\[[0-9;]*m//g\" | {} {}/{}'".format(
        cmd,
        instance_data['binaries']['sed'],
        instance_data['binaries']['cronolog'],
        instance_data['paths']['log'],
        instance_data['setup_params']['cronolog_template']
    )

def get_node_params(instance_data, daemonize=False, as_string=False, first_run=False):
    stack = []
    stack.append('--db')
    stack.append(instance_data['paths']['db'])

    stack.append('--global-config')
    stack.append(instance_data['configs']['global'])

    stack.append('--verbosity')
    stack.append(str(instance_data['setup_params']['service_verbosity']))

    if instance_data['setup_params']['service_threads']:
        stack.append('--threads')
        stack.append(str(instance_data['setup_params']['service_threads']))


    if instance_data['mode'] == 'node':
        stack.append('--session-logs')
        stack.append("{}/session-logs.log".format(instance_data['paths']['log']))

        if instance_data['setup_params']['state_ttl']:
            stack.append('--state-ttl')
            stack.append(str(instance_data['setup_params']['state_ttl']))

        if instance_data['setup_params']['archive_ttl']:
            stack.append('--archive-ttl')
            stack.append(str(instance_data['setup_params']['archive_ttl']))

        if instance_data['setup_params']['sync_before'] and first_run:
            stack.append('--sync-before')
            stack.append(str(instance_data['setup_params']['sync_before']))

    if not instance_data['setup_params']['use_cronolog']:
        stack.append('--logname')
        stack.append("{}/node".format(instance_data['paths']['log']))

    if daemonize:
        stack.append('--daemonize')

    if as_string:
        result = ""
        for element in stack:
            result += " {}".format(element)

        return result
    else:
        return stack

def create_paths(paths, force=False):
    for element in ['home', 'etc', 'db', 'log', 'init_log', 'backup']:
        mk_path(paths[element])

    mk_path("{}/keys".format(paths['etc']))
    mk_path("{}/initial".format(paths['backup']))

def mk_path(path, log=None):
    if not os.path.exists(path):
        if log:
            log(inspect.currentframe().f_code.co_name, 3, "Creating path {}".format(path))
        os.makedirs(path)

def no_force_exit(reason, log=None):
    if log:
        log(inspect.currentframe().f_code.co_name, 1, "{}, fix the problem or specify --force flag".format(reason))
    sys.exit(1)

def get_datetime_string(timestamp=time.time()):
    return time.strftime("%d.%m.%Y %H:%M:%S %Z", time.localtime(timestamp))

def get_unused_port(used_ports):
    port = None
    while not port:
        candidate = random.randint(10000, 49151)
        if candidate not in used_ports and not is_port_in_use(candidate):
            port = candidate
            used_ports.append(port)

    return port

def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def mk_keys(basename, dist_path, log=None):
    process_args = ["{}/bin/generate-random-id".format(dist_path),
                    "--mode", "keys",
                    "--name", basename]
    try:
        process = subprocess.run(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=10)
        if process.returncode > 0:
            if log:
                log(inspect.currentframe().f_code.co_name, 1, "Keys generation failed: {}".format(process.stderr.decode("utf-8")))
            sys.exit(1)
        else:
            hashes = process.stdout.decode("utf-8").split(' ')
            with open("{}.pub".format(basename), "rb+") as fd:
                pk_hash = base64.b64encode(fd.read()[4:]).decode()

            return [hashes[0].strip(), hashes[1].strip(), pk_hash]
    except Exception as e:
        if log:
            log(inspect.currentframe().f_code.co_name, 1, "Execution of validator-engine failed: {}".format(e))
        sys.exit(1)

def parse_template(template, stash):
    for element in stash:
        template = template.replace(element, stash[element])

    return template


def chown(path, uid, gid, recursive=False):
    if recursive:
        for root, dirs, files in os.walk(path):
            for element in dirs:
                os.chown(os.path.join(root, element), uid, gid)

            for element in files:
                os.chown(os.path.join(root, element), uid, gid)
    else:
        os.chown(path, uid, gid)

def confirmation(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

def log(facility, level, message):
    global verbosity
    levels = ['NONE', 'ERROR', 'INFO', 'DEBUG']
    if level <= verbosity:
        print("{} [{}|{}]: {}".format(get_datetime_string(),
                                      facility,
                                      levels[level],
                                      message))

def vc_exec(console_bin, server_address, server_port, server_key, client_key, cmd):
    args = [console_bin,
            "--address", "{}:{}".format(server_address, server_port),
            "--key", client_key,
            "--pub", server_key,
            "--verbosity", "0",
            "--cmd", cmd]

    process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=3)
    return process.stdout.decode("utf-8")


if __name__ == '__main__':
    run()
