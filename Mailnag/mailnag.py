#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# mailnag.py
#
# Copyright 2011 Patrick Ulbrich <zulu99@gmx.net>
# Copyright 2011 Leighton Earl <leighton.earl@gmx.com>
# Copyright 2011 Ralf Hersel <ralf.hersel@gmx.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#

import os
from gi.repository import GObject, GLib
import signal

from common.config import read_cfg, cfg_exists, cfg_folder
from common.utils import set_procname
from common.accountlist import AccountList
from daemon.mailchecker import MailChecker
from daemon.idlers import Idlers

def read_config():
	if not cfg_exists():
		return None
	else:
		return read_cfg()


def write_pid(): # write Mailnags's process id to file
	pid_file = os.path.join(cfg_folder, 'mailnag.pid')
	f = open(pid_file, 'w')
	f.write(str(os.getpid()))
	f.close()


def delete_pid(): # delete file mailnag.pid
	pid_file = os.path.join(cfg_folder, 'mailnag.pid')
	if os.path.exists(pid_file):
		os.remove(pid_file)


def cleanup():
	# clean up resources
	try:
		for n in mailchecker.notifications.itervalues():
			n.close()
	except NameError: pass
	
	try:
		idlers.dispose()
	except NameError: pass
	
	delete_pid()


def sig_handler(signum, frame):
	if mainloop != None:
		mainloop.quit()


def main():
	global mailchecker, mainloop, idlers
	
	mainloop = None
	
	set_procname("mailnag")
	
	GObject.threads_init()
	
	signal.signal(signal.SIGTERM, sig_handler)
	
	try:
		write_pid() # write Mailnag's process id to file
		cfg = read_config()
		
		if (cfg == None):
			print 'Error: Cannot find configuration file. Please run mailnag_config first.'
			exit(1)
		
		accounts = AccountList()
		accounts.load_from_cfg(cfg, enabled_only = True)
		
		mailchecker = MailChecker(cfg, accounts)
		
		# immediate check
		mailchecker.check(firstcheck = True)
		
		# start polling thread for POP3 accounts and
		# IMAP accounts without idle support
		if sum(1 for acc in accounts if ((not acc.imap ) or (acc.imap and not acc.idle))) > 0:
			check_interval = int(cfg.get('general', 'check_interval'))
			GObject.timeout_add_seconds(60 * check_interval, mailchecker.check)
		
		# start idler threads for IMAP accounts with idle support
		if sum(1 for acc in accounts if (acc.imap and acc.idle)) > 0:
			idlers = Idlers(accounts, mailchecker.check)
			idlers.run()
		
		mainloop = GObject.MainLoop()
		mainloop.run()
	except KeyboardInterrupt:
		pass # ctrl+c pressed
	finally:
		cleanup()


if __name__ == '__main__': main()
