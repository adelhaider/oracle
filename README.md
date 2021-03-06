This is just an example .md file taken from
https://gist.githubusercontent.com/jagtesh/5531300/raw/a9ba30468aa846cc4ab426f504135c762f811a10/split_tunneling.md

______________________________________________________________________________


Table of Contents

  1. DISCLAIMER
	2. Status
	3. Introduction
	4. Security issues
	5. DNS
	6. Web Proxy
	7. Extended connection script
	8. Example
	9. Changelog

______________________________________________________________________________


1. DISCLAIMER
=============

Misusing the information provided in this document, you can open a security
hole in the network protected by VPN.
Nor the authors of this document nor the developers of vpnc can be considered
responsible for any damage or legal issue caused by using the information in
this document.
If you are not fully aware of all the possible consequences created by your
actions, DON'T use any of the configuration below.


2. Status
=========

Following information has been tested only with Linux host and Nortel server.
Any support or suggestion to improve this tutorial and to include other hosts
and servers is warmly welcome.


3. Introduction
===============

A usual VPN configuration routes all the network connections through the VPN
tunnel.
Split tunnel is able to discriminate between IPs that have to be accessed
through the VPN tunnel and IPs that have to be accessed directly.
Practically, split tunnel lets your computer accessing the secure network
through the VPN tunnel, while also accessing internet directly.

Split tunnel is usually set and controlled by the VPN server configuration and
deployed to VPN client.
This tutorial explains how to use vpnc to set your own split tunnel on client
side, bypassing server setting.
Possible applications are:
- fixing, on client side, a server misconfiguration;
- enabling split tunnel when server doesn't offer it.

Several users connect to VPN just to access their corporate internal mail
server. When VPN is on, lack of split tunnel stops every connection not
supported or allowed in the corporate network (e.g. video, voip, chat, ssh) or
dramatically slows down connection to other internet resources.

Thanks to split tunnel, you can still read mail form corporate server, while
enjoying full internet experience.


4. Security issues
==================

Split tunnel is usually not enabled in VPN servers, since it can open a
security hole.
In fact, in a split tunnel configuration, your computer can act as a bridge
between internet and the protected network.
Typical risky situations are:
- your computer is not fully secured (e.g. infected by virus or, even worst,
  part of a botnet);
- your computer has active accounts that can be accessed remotely;
- you use a pear-to-pear SW that builds a mesh network.
For such reason, most VPN server administrator guide discourage split tunnel,
and system administrators usually don't take risk, keeping it disabled.
So, be aware that any split tunnel on client side is done "by you" "at your
own risk!"
My personal suggestion is to enable it ONLY in specific situation, and only
for few dedicated servers in the protected network (e.g. mail server). List
one by one each server you need to connect with, and never enable a whole
subnet.


5. DNS
======

Consider that your computer only manages "one" set of DNS servers.
Usually corporate networks deploy their own DNS server, that only resolves
corporate internal name space.
In a split tunnel your computer cannot inquire either corporate and internet
DNS, but only one of them.
You have now to decide which DNS you have to use, while you can use the local
static lookup table in /etc/hosts for the other case.

Of course, you can setup a local DNS server, that inquires either corporate or
internet DNS. Such arrangement is not covered by this tutorial.

If you only want to use the corporate mail server (supposed having fix IP),
you can resolve it with /etc/hosts, and use internet DNS for all other cases.


6. Web Proxy
============

Some corporate network is organized with a proxy server to access external web
sites that can also be used to access internal ones.
In this case, you do not have to configure routes to every corporate internal
website you want to access, but just route to the proxy server.
You can then use the same proxy to access internet web sites, or you can use a
browser proxy switch (e.g. FoxyProxy http://foxyproxy.mozdev.org/ for Firefox)
to select the best routing.


7. Extended connection script
=============================

Current vpnc just follows what VPN server configures.
To setup your own split tunnel, there is no need to modify vpnc code, nor the
connection script /etc/vpnc/vpnc-script.
It is possible to create an extension of such script; practically a script
that sets few variables and in turns calls /etc/vpnc/vpnc-script script.
More details in example below.


8. Example
==========
In the following example we will consider:
- Linux host (maybe valid for other UNIXes);
- Nortel server (maybe works as is also with Cisco);
- split tunnel to access just few hosts inside the corporate network;
- hosts in corporate network have fixed IP addresses;
- DNS and all other routes to internet.


8.1 Step 1
----------

List all the hosts you need to access in the corporate network.
In the following example we will consider:
- mail server, to read messages: pop3.mycom.com;
- smtp server, to send messages out: smtp.mycom.com;
- ldap server, to search mail accounts: ldap.mycom.com;
- internet proxy, to access internal websites: proxy.mycom.com.
Avoid a long list; keep security in mind and just map what you really need.


8.2 Step 2
----------

Resolve IP address of all the names you listed in Step 1, and put them in your
local file /etc/hosts. We suppose all of them are fixed IP.
Sometimes two or more servers are mapped to the same IP. Practically it is the
same server that implements multiple functions. In the example below, we
suppose that pop3 and smtp services are on the same server.
Example of /etc/hosts:
	______________________________________________________________________
	127.0.0.1	localhost.localdomain localhost
	::1		localhost6.localdomain6 localhost6
	10.0.0.130	pop3.mycom.com smtp.mycom.com
	10.0.14.1	ldap.mycom.com
	10.1.0.5	proxy.mycom.com
	______________________________________________________________________


8.3 Step 3
----------

Create a copy of your working vpnc config file:
#> cp /etc/vpnc/corp.conf /etc/vpnc/split.conf


8.4 Step 4
----------

Edit the new file "split.conf" and add the following line:
	Script /etc/vpnc/vpnc-script-corp-split
It will force this new configuration to use a special script file.


8.5 Step 5
----------

Create the file /etc/vpnc/vpnc-script-corp-split with following content
	______________________________________________________________________
	#!/bin/sh

	# Add one IP to the list of split tunnel
	add_ip ()
	{
		export CISCO_SPLIT_INC_${CISCO_SPLIT_INC}_ADDR=$1
	        export CISCO_SPLIT_INC_${CISCO_SPLIT_INC}_MASK=255.255.255.255
	        export CISCO_SPLIT_INC_${CISCO_SPLIT_INC}_MASKLEN=32
	        export CISCO_SPLIT_INC=$(($CISCO_SPLIT_INC + 1))
	}

	# Initialize empty split tunnel list
	export CISCO_SPLIT_INC=0

	# Delete DNS info provided by VPN server to use internet DNS
	# Comment following line to use DNS beyond VPN tunnel
	unset INTERNAL_IP4_DNS

	# List of IPs beyond VPN tunnel
	add_ip 10.0.0.130	# pop3.mycom.com and smtp
	add_ip 10.0.14.1	# ldap.mycom.com
	add_ip 10.1.0.5		# proxy.mycom.com

	# Execute default script
	. /etc/vpnc/vpnc-script

	# End of script
	______________________________________________________________________

Parameter passed to "add_ip" is used, in /etc/vpnc/vpnc-script, to set routing
table by running either "ip" or "route" command, depending on system
configuration.
While "route" accepts both host names and IP in the command line, "ip"
strictly requires numeric IP.
This is quite annoying, since would be easier using only host names in the
script abobe, keeping numeric IP relations in /etc/hosts only.
Eventually, could be possible improving the script above by resolving names
before running /etc/vpnc/vpnc-script.
The command "gethostip" could be used for name resolution. Does anybody knows
if the command "gethostip" is present in every Linux distro?


8.6 Step 6
----------

At last, provide the proper execution permission:
#> chmod 755 /etc/vpnc/vpnc-script-corp-split

That's all, folks!
You can now run:
#> vpnc split.conf

Reading routing table, you can verify the split is active.
#> route
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
proxy.mycom.com *               255.255.255.255 UH    0      0        0 tun0
ldap.mycom.com  *               255.255.255.255 UH    0      0        0 tun0
pop3.mycom.com  *               255.255.255.255 UH    0      0        0 tun0
vpn.mycom.com   192.168.1.1     255.255.255.255 UGH   0      0        0 eth0
192.168.1.0     *               255.255.255.0   U     0      0        0 eth0
10.2.0.0        *               255.255.255.0   U     0      0        0 tun0
169.254.0.0     *               255.255.0.0     U     0      0        0 eth0
default         192.168.1.1     0.0.0.0         UG    0      0        0 eth0


9 Changelog
===========

2009-02-28	v0.1	Antonio Borneo <borneo.antonio at gmail.com>
	* first version
