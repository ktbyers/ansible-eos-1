########
Overview
########

************
Introduction
************
Ansible is a configuration management framework that provides an automated
infrastructure for managing systems devices and applications. Ansible provides
this functionality using an agent-less approach that focuses on management of
the destination device and/or application over SSH. Ansible achieves it vision
through the implementation of playbooks and modules. Playbooks, which are in
turn comprised of a series of tasks to be executed on a host or group of
hosts, provide the fundamental workflow in Ansible. Modules are host and/or
application specific that perform the operations based on the directives of
the tasks and playbooks. Complete details about Ansible can be found at
their `website <http://docs.ansible.com/index.html>`_.

****************
Connection Types
****************
Ansible provides three distinctly different connection types each providing
a different method for connecting the Ansible runtime components
(playbooks, modules) with the destination device. A summary of the connection
types are below.

SSH Connection
==============
When operating in this mode, Ansible will connect to the destination host
using an encrypted SSH session. The SSH connection is established using
either the hosts native SSH binary or using the
`Paramiko <http://docs.ansible.com/intro_getting_started.html#remote-connection-information>`_
library. Since it uses SSH as the transport, the Ansible connection needs to
be able to authenticate to the remote system and expects to operate in a
Linux shell environment

Local connections
=================
When a host or task is operating with a local connection, tasks are executed
from the Ansible host where the job was initiated. Local connections allow
Ansible to make use of API transports and remove the need for establishing an
SSH connection to the target device.

Accelerated mode
================
Ansible supported (since v0.8) a mode of operation known as Fireball mode.
Fireball mode has since been depreciated in favor of accelerated mode (as of v1.3).
Accelerated mode connects to the destination node and starts a daemon that is
used for the remainder of the transaction. More details about accelerated
mode can be found at this link.

In addition to the connection types discussed above, Ansible also supports
a pull model. The pull model works in conjunction with SCM systems to perform
its duties locally on the node. The pull model executes a local utility that
retrieves the configuration data and proceeds to execute all of the activity
locally on the node.


********************
The Ansible EOS Role
********************

Integration with the Python Client for eAPI
===========================================
The Ansible Role for EOS does not rely on jsonrpclib to control
the node's Command API interface, rather, the `Python Client for eAPI <https://github.com/arista-eosplus/pyeapi>`_
is used.


Topologies
==========
Above, we discussed how Ansible is typically used to control a node. These
principles remain true for Arista EOS nodes, however, there are some nuances
that are important to understand. Next, we will discuss the two main
methods used to control an Arista EOS node using Ansible.

.. image:: _img/ansible-deploy.jpg
        :width: 85%
        :align: center

The illustration above demonstrates a typical scenario. You, as the user, want
to execute an Ansible Playbook on one (or many) of your Arista nodes. From the
user's perspective the interaction with the Ansible Control Host is the same,
from your shell you would type

.. code-block:: console

  ansible-playbook eos.yaml

but the way in which the playbook is executed will differ between Option A and
Option B. Let's discuss those differences below.

Option A
========
This method follows the traditional Ansible control procedure, namely:

1. Execute ``ansible-playbook eos.yaml`` from the Ansible Control Host
2. Collect Fact information from the node
3. Download the module to the node
4. Execute the module on the node
5. Read stdout and parse it into JSON
6. Return the result to the Ansible Control Host

**Assumption 1**
You'll notice that this method uses SSH to communicate with the node. This
implies that you have already included the Ansible Control Host's public SSH
key in the nodes ``authorized_keys`` file, or you are providing a password
when the playbook executes.

**Assumption 2**
Pyeapi is being used by the module to make configuration changes on the
node. This implies that ``pyeapi`` is already installed on the node. The pyeapi
module is NOT installed on Arista EOS nodes by default, so installation would
be required by the user.


Option B
========
This method uses the ``connection: local`` feature within the ``eos.yaml``
playbook. This changes how the playbook gets executed in the following way:

1. Include ``connection: local`` in ``eos.yaml``
2. Execute ``ansible-playbook eos.yaml`` from the Ansible Control Host
3. pyeapi consults the local eapi.conf file which provide node connection information
4. Collect Fact information from the node
5. Execute the module on the Ansible Control Host
6. Read stdout and parse it into JSON
7. Return the result to the Ansible Control Host

**Assumption 1**
Here, the connection between the Ansible Control Host and the Arista node is
an eAPI connection. This implies that you have an ``eapi.conf`` file on your
Ansible Control Host that contains the connection parameters for this node.
The caveat here is that the password for the eAPI connection is stored as
plaintext in ``eapi.conf``.


*************
Ansible Tower
*************
Ansible provides a product that implements a web based interface and REST API
known as `Tower <http://www.ansible.com/tower>`_. The web interface provides
some additional capabilities to the base Ansible framework around role based
access and programmatic interface to the Ansible environment.
