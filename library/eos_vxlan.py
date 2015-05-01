#!/usr/bin/python
#
# Copyright (c) 2014, Arista Networks, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
#   Neither the name of Arista Networks nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
DOCUMENTATION = """
---
module: eos_vxlan
short_description: Manage logical VxLAN interfaces in EOS
description:
  - The eos_vxlan module manages the logical VxLAN interface configuration
    on Arista EOS nodes.
version_added: 1.0.0
category: VXLAN
author: Arista EOS+
requirements:
  - Arista EOS 4.13.7M or later with command API enabled
  - Python Client for eAPI 0.3.0 or later
notes:
  - All configuration is idempotent unless otherwise specified
  - Supports eos metaparameters for using the eAPI transport
  - Supports stateful resource configuration.
options:
  name:
    description:
      - The unique interface identifier name.  The interface name must use
        the full interface name (no abbreviated names).  For example,
        interfaces should be specified as Ethernet1 not Et1
      - "Note: The name parameter only accepts Vxlan1 as the identifier"
    required: true
    default: null
    choices: []
    aliases: []
    version_added: 1.0
  enable:
    description:
      - Configures the administrative state for the interface.  Setting
        the value to true will adminstrative enable the interface and
        setting the value to false will administratively disable the
        interface.  The EOS default value for enable is true
    required: false
    default: true
    choices: BOOLEANS
    aliases: []
    version_added: 1.0
  description:
    description:
      - Configures a one lne ASCII description for the interface.  The EOS
        default value for description is None
    required: false
    default: null
    choices: []
    aliases: []
    version_added: 1.0
  source_interface:
    description:
      - Configures the vxlan source-interface value which directs the
        interface to use the specified source interface address to source
        messages from.  The configured value must be a Loopback interface.
        The EOS default value for source interface is None.
    required: false
    default: null
    choices: []
    aliases: []
    version_added: 1.0
  multicast_group:
    description:
      - Configures the vxlan multicast-group address used for flooding
        traffic between VTEPs.  This value must be a valid multicast
        address in the range of 224/8.  The EOS default value for vxlan
        multicast-group is None.
    required: false
    default: null
    choices: []
    aliases: []
    version_added: 1.0
  udp_port:
    description:
      - Configures the vxlan udp-port value used to terminate mutlicast
        messages between VTEPs.  This value must be an integer in the
        range of 1024 to 65535.  The EOS default value for vxlan
        udp-port is 4789.
    required: false
    default: null
    choices: []
    aliases: []
    version_added: 1.0
"""

EXAMPLES = """

- name: ensures the vxlan interface is configured
  eos_vxlan: name=Vxlan1 state=present enable=yes

- name: ensures the vxlan interface is not configured
  eos_vxlan: name=Vxlan1 state=absent

- name: configures the vxlan source interface
  eos_vxlan: name=Vxlan1 source_interface=Loopback0

"""
#<<EOS_COMMON_MODULE_START>>

import syslog
import collections

from ansible.module_utils.basic import *

try:
    import pyeapi
    PYEAPI_AVAILABLE = True
except ImportError:
    PYEAPI_AVAILABLE = False

DEFAULT_SYSLOG_PRIORITY = syslog.LOG_NOTICE
DEFAULT_CONNECTION = 'localhost'
TRANSPORTS = ['socket', 'http', 'https', 'http_local']

class EosAnsibleModule(AnsibleModule):

    meta_args = {
        'config': dict(),
        'username': dict(),
        'password': dict(),
        'host': dict(),
        'connection': dict(default=DEFAULT_CONNECTION),
        'transport': dict(choices=TRANSPORTS),
        'port': dict(),
        'debug': dict(type='bool', default='false'),
        'logging': dict(type='bool', default='true')
    }

    stateful_args = {
        'state': dict(default='present', choices=['present', 'absent']),
    }

    def __init__(self, stateful=True, *args, **kwargs):

        kwargs['argument_spec'].update(self.meta_args)

        self._stateful = stateful
        if stateful:
            kwargs['argument_spec'].update(self.stateful_args)

        super(EosAnsibleModule, self).__init__(*args, **kwargs)

        self.result = dict(changed=False, changes=dict())

        self._debug = kwargs.get('debug') or self.boolean(self.params['debug'])
        self._logging = kwargs.get('logging') or self.params['logging']

        self.log('DEBUG flag is %s' % self._debug)

        self.debug('pyeapi_version', self.check_pyeapi())
        self.debug('stateful', self._stateful)
        self.debug('params', self.params)

        self._attributes = self.map_argument_spec()
        self._node = self.connect()

        self._instance = None

        self.desired_state = self.params['state'] if self._stateful else None
        self.exit_after_flush = kwargs.get('exit_after_flush')

    @property
    def instance(self):
        if self._instance:
            return self._instance

        func = self.func('instance')
        if not func:
            self.fail('Module does not support "instance"')

        try:
            self._instance = func(self)
        except Exception as exc:
            self.fail('instance[error]: %s' % exc.message)

        self.log("called instance: %s" % self._instance)
        return self._instance

    @property
    def attributes(self):
        return self._attributes

    @property
    def node(self):
        if self._node:
            return self._node
        self._node = self.connect()
        return self._node

    def check_pyeapi(self):
        if not PYEAPI_AVAILABLE:
            self.fail('Unable to import pyeapi, is it installed?')
        return pyeapi.__version__

    def map_argument_spec(self):
        """map_argument_spec maps only the module argument spec to attrs

        This method will map the argumentspec minus the meta_args to attrs
        and return the attrs.  This returns a dict object that includes only
        the original argspec plus the stateful_args (if self._stateful=True)

        Returns:
            dict: Returns a dict object that includes the original
                argument_spec plus stateful_args with values minus meta_args

        """
        keys = set(self.params).difference(self.meta_args)
        attrs = dict()
        attrs = dict([(k, self.params[k]) for k in self.params if k in keys])
        return attrs

    def create(self):
        if not self.check_mode:
            func = self.func('create')
            if not func:
                self.fail('Module must define "create" function')
            return self.invoke(func, self)

    def remove(self):
        if not self.check_mode:
            func = self.func('remove')
            if not func:
                self.fail('Module most define "remove" function')
            return self.invoke(func, self)

    def flush(self, exit_after_flush=False):
        self.exit_after_flush = exit_after_flush

        if self.desired_state == 'present' or not self._stateful:
            if self.instance.get('state') == 'absent':
                changed = self.create()
                self.result['changed'] = changed or True
                self.refresh()

            changeset = self.attributes.viewitems() - self.instance.viewitems()

            if self._debug:
                self.debug('desired_state', self.attributes)
                self.debug('current_state', self.instance)

            changes = self.update(changeset)
            if changes:
                self.result['changes'] = changes
                self.result['changed'] = True

            self._attributes.update(changes)

            flush = self.func('flush')
            if flush:
                self.invoke(flush, self)

        elif self.desired_state == 'absent' and self._stateful:
            if self.instance.get('state') == 'present':
                changed = self.remove()
                self.result['changed'] = changed or True

        elif self._stateful:
            if self.desired_state != self.instance.get('state'):
                changed = self.invoke(self.instance.get('state'))
                self.result['changed'] = changed or True

        self.refresh()
        self.result['instance'] = self.instance

        if self.exit_after_flush:
            self.exit()

    def update(self, changeset):
        changes = dict()
        for key, value in changeset:
            if value is not None:
                changes[key] = value
                func = self.func('set_%s' % key)
                if func and not self.check_mode:
                    try:
                        self.invoke(func, self)
                    except Exception as exc:
                        self.fail(exc.message)
        return changes

    def connect(self):
        if self.params['config']:
            pyeapi.load_config(self.params['config'])

        config = dict()

        if self.params['connection']:
            config = pyeapi.config_for(self.params['connection'])
            if not config:
                msg = 'Connection name "%s" not found' % self.params['connection']
                self.fail(msg)

        if self.params['username']:
            config['username'] = self.params['username']

        if self.params['password']:
            config['password'] = self.params['password']

        if self.params['transport']:
            config['transport'] = self.params['transport']

        if self.params['port']:
            config['port'] = self.params['port']

        if self.params['host']:
            config['host'] = self.params['host']

        if 'transport' not in config:
            self.fail('Connection must define a transport')

        connection = pyeapi.client.make_connection(**config)
        node = pyeapi.client.Node(connection)

        try:
            node.enable('show version')
        except (pyeapi.eapilib.ConnectionError, pyeapi.eapilib.CommandError):
            self.fail('unable to connect to %s' % node)
        else:
            self.log('Connected to node %s' % node)
            self.debug('node', str(node))

        return node

    def config(self, commands):
        self.result['changed'] = True
        if not self.check_mode:
            self.node.config(commands)

    def api(self, module):
        return self.node.api(module)

    def func(self, name):
        return globals().get(name)

    def invoke(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            self.fail(exc.message)

    def invoke_function(self, name, *args, **kwargs):
        func = self.func(name)
        if func:
            return self.invoke(func, *args, **kwargs)

    def fail(self, msg):
        self.invoke_function('on_fail', self)
        self.log('ERROR: %s' % msg, syslog.LOG_ERR)
        self.fail_json(msg=msg)

    def exit(self):
        self.invoke_function('on_exit', self)
        self.log('Module completed successfully')
        self.exit_json(**self.result)

    def refresh(self):
        self._instance = None

    def debug(self, key, value):
        if self._debug:
            if 'debug' not in self.result:
                self.result['debug'] = dict()
            self.result['debug'][key] = value

    def log(self, message, priority=None):
        if self._logging:
            syslog.openlog('ansible-eos')
            priority = priority or DEFAULT_SYSLOG_PRIORITY
            syslog.syslog(priority, str(message))

    @classmethod
    def add_state(cls, name):
        cls.stateful_args['state']['choices'].append(name)

#<<EOS_COMMON_MODULE_END>>

def instance(module):
    """ Returns the vxlan interface properties for the specified name
    """
    name = module.attributes['name']
    result = module.node.api('interfaces').get(name)
    _instance = dict(name=name, state='absent')
    if result:
        _instance['state'] = 'present'
        _instance['enable'] = not result['shutdown']
        _instance['description'] = result['description']
        _instance['source_interface'] = result['source_interface']
        _instance['multicast_group'] = result['multicast_group']
        _instance['udp_port'] = result['udp_port']
    return _instance

def create(module):
    """Creates a new instance of the Vxlan interface on the node
    """
    name = module.attributes['name']
    module.log('Invoked create for eos_vxlan[%s]' % name)
    module.node.api('interfaces').create(name)

def remove(module):
    """Removes an existing instance of the Vxlan interface on the node
    """
    name = module.attributes['name']
    module.log('Invoked remove for eos_vxlan[%s]' % name)
    module.node.api('interfaces').delete(name)

def set_description(module):
    """ Configures the description attribute for the interface
    """
    value = module.attributes['description']
    name = module.attributes['name']
    module.log('Invoked set_description for eos_vxlan[%s] '
               'with value %s' % (name, value))
    if value == '':
        module.node.api('interfaces').set_description(name, default=True)
    else:
        module.node.api('interfaces').set_description(name, value)

def set_enable(module):
    """ Configures the enable attribute for the interface
    """
    value = not module.attributes['enable']
    name = module.attributes['name']
    module.log('Invoked set_enable for eos_vxlan[%s] '
               'with value %s' % (name, value))
    module.node.api('interfaces').set_shutdown(name, value)

def set_source_interface(module):
    """ Configures the source interface attribute for the interface
    """
    value = module.attributes['source_interface']
    name = module.attributes['name']
    module.log('Invoked set_source_interface for eos_vxlan[%s] '
               'with value %s' % (name, value))
    module.node.api('interfaces').set_source_interface(name, value)


def set_multicast_group(module):
    """ Configures the multicast group attribute for the interface
    """
    value = module.attributes['multicast_group']
    name = module.attributes['name']
    module.log('Invoked set_multicast_group for eos_vxlan[%s] '
               'with value %s' % (name, value))
    module.node.api('interfaces').set_multicast_group(name, value)

def set_udp_port(module):
    """ Configures the multicast group attribute for the interface
    """
    value = module.attributes['udp_port']
    name = module.attributes['name']
    module.log('Invoked set_udp_port for eos_vxlan[%s] '
               'with value %s' % (name, value))
    module.node.api('interfaces').set_udp_port(name, value)

def validate_udp_port(value):
    if value < 1024 or value > 65536:
        raise AttributeError('udp_port must be between 1024 and 65535')

def main():
    """ The main module routine called when the module is run by Ansible
    """

    argument_spec = dict(
        name=dict(),
        enable=dict(type='bool', default='true'),
        description=dict(),
        source_interface=dict(),
        multicast_group=dict(),
        udp_port=dict(type='int')
    )

    module = EosAnsibleModule(argument_spec=argument_spec,
                              supports_check_mode=True)

    module.flush(True)

main()
