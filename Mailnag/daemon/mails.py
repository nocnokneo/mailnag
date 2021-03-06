#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# mails.py
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

import time
import urllib2
import sys
import email
from email.header import decode_header

from daemon.mail import Mail

class Mails:
	def __init__(self, cfg, accounts):
		self.cfg = cfg
		self.accounts = accounts
		
		
	def get_mail(self, sort_order):
		mail_list = []													# initialize list of mails
		mail_ids = []													# initialize list of mail ids
		while not self.is_online(): time.sleep(5)						# wait for internet connection
		filter_enabled = bool(int(self.cfg.get('filter', 'filter_enabled')))	# get filter switch

		for acc in self.accounts:
			srv = acc.get_connection()									# get server connection for this account
			if srv == None:
				continue												# continue with next account if server is empty
			elif acc.imap:												# IMAP
				folder_list = acc.folder.split(',')						# make a list of folders
				mail_count = 0											# reset email counter
				if folder_list[0] == '':
					folder_list = ['INBOX']
				for folder in folder_list:
									
					tmp = folder.strip()
					srv.select(tmp, readonly=True) # select IMAP folder
					try:
						status, data = srv.search(None, 'UNSEEN') # ALL or UNSEEN
					except:
						print "The folder:", tmp, "does not exist, using INBOX instead"
						try:
							srv.select('INBOX', readonly=True) # If search fails select INBOX and try again
							status, data = srv.search(None, 'UNSEEN') # ALL or UNSEEN
						except:
							print "INBOX Could not be found", sys.exc_info()[0]

					if status != 'OK' or None in [d for d in data]:
						print "Folder", folder, "in status", status, "| Data:", data, "\n"
						continue										# Bugfix LP-735071
					for num in data[0].split():
						typ, msg_data = srv.fetch(num, '(BODY.PEEK[HEADER])')	# header only (without setting READ flag)
						for response_part in msg_data:
							if isinstance(response_part, tuple):
								try:
									msg = email.message_from_string(response_part[1])
								except:
									print "Could not get IMAP message." # debug
									continue
								try:
									try:
										sender = self.format_header('sender', msg['From'])	# get sender and format it
									except KeyError:
										print "KeyError exception for key 'From' in message." # debug
										sender = self.format_header('sender', msg['from'])
								except:
									print "Could not get sender from IMAP message." # debug
									sender = "Error in sender"
								try:
									try:
										datetime, seconds = self.format_header('date', msg['Date'])	# get date and format it
									except KeyError:
										print "KeyError exception for key 'Date' in message." # debug
										datetime, seconds = self.format_header('date', msg['date'])
								except:
									print "Could not get date from IMAP message." # debug
									datetime = time.strftime('%Y.%m.%d %X')					# take current time as "2010.12.31 13:57:04"
									seconds = time.time()									# take current time as seconds
								try:
									try:
										subject = self.format_header('subject', msg['Subject'])	# get subject and format it
									except KeyError:
										print "KeyError exception for key 'Subject' in message." # debug
										subject = self.format_header('subject', msg['subject'])
								except:
									print "Could not get subject from IMAP message." # debug
									subject = 'Error in subject'
								try:
									id = msg['Message-Id']
								except:
									print "Could not get id from IMAP message."				# debug
									id = None                                               # prepare emergency 
								
								if id == None or id == '':
									id = str(hash(subject))				# create emergency id
						
						if id not in mail_ids:							# prevent duplicates caused by Gmail labels
							if not (filter_enabled and self.in_filter(sender + subject)):		# check filter
								mail_list.append(Mail(seconds, subject, \
									sender, datetime, id, acc.name))
								mail_count += 1							# increment mail counter for this IMAP folder
								mail_ids.append(id)						# add id to list
				
				acc.mail_count = mail_count								# store number of emails per account
				srv.close()
				srv.logout()
			else:														# POP
				mail_total = len(srv.list()[1])							# number of mails on the server
				mail_count = 0											# reset number of relevant mails
				for i in range(1, mail_total+1):						# for each mail
					try:
						message = srv.top(i, 0)[1]						# header plus first 0 lines from body
					except:
						print "Could not get POP message."				# debug
						continue
					message_string = '\n'.join(message)					# convert list to string
					try:
						msg = dict(email.message_from_string(message_string))	# put message into email object and make a dictionary
					except:
						print "Could not get msg from POP message."	# debug
						continue
					try:
						try:
							sender = self.format_header('sender', msg['From'])	# get sender and format it
						except KeyError:
							print "KeyError exception for key 'From' in message."	# debug
							sender = self.format_header('sender', msg['from'])
					except:
						print "Could not get sender from POP message."	# debug
						sender = "Error in sender"
					try:
						try:
							datetime, seconds = self.format_header('date', msg['Date'])	# get date and format it
						except KeyError:
							print "KeyError exception for key 'Date' in message."	# debug
							datetime, seconds = self.format_header('date', msg['date'])
					except:
						print "Could not get date from POP message."	# debug
						datetime = time.strftime('%Y.%m.%d %X')			# take current time as "2010.12.31 13:57:04"
						seconds = time.time()							# take current time as seconds
					try:
						try:
							subject = self.format_header('subject', msg['Subject'])	# get subject and format it
						except KeyError:
							print "KeyError exception for key 'Subject' in message."	# debug
							subject = self.format_header('subject', msg['subject'])
					except:
						print "Could not get subject from POP message."
						subject = 'Error in subject'
					try:
						uidl = srv.uidl(i)								# get id
					except:
						print "Could not get id from POP message."		# debug
						uidl = None                                         # prepare emergency
					
					if uidl == None or uidl == '':	
						uidl = str(hash(subject))						# create emergency id
					
					id = acc.user + uidl.split(' ')[2]					# create unique id
					if not (filter_enabled and self.in_filter(sender + subject)):	# check filter
						mail_list.append(Mail(seconds, subject, sender, \
							datetime, id, acc.name))
						mail_count += 1									# increment mail counter for this IMAP folder
					acc.mail_count = mail_count							# store number of emails per account
				srv.quit()												# disconnect from Email-Server
		mail_list = self.sort_mails(mail_list, sort_order)				# sort mails
		sys.stdout.flush()												# write stdout to log file
		return mail_list


	def is_online(self):												# check for internet connection
		try:
			urllib2.urlopen("http://www.google.com/")
			return True
		except:
			return False


	def in_filter(self, sendersubject):									# check if filter appears in sendersubject
		status = False
		filter_text = self.cfg.get('filter', 'filter_text')
		filter_list = filter_text.replace('\n', '').split(',')			# convert text to list
		for filter_item in filter_list:
			filter_stripped_item = filter_item.strip()					# remove CR and white space
			
			if len(filter_stripped_item) == 0:
				continue
			
			if filter_stripped_item.lower() in sendersubject.lower():
				status = True											# subject contains filter item
				break
		return status


	def sort_mails(self, mail_list, sort_order):						# sort mail list
		sort_list = []
		for mail in mail_list:
			sort_list.append([mail.seconds, mail])						# extract seconds from mail instance
		sort_list.sort()												# sort asc
		if sort_order == 'desc':
			sort_list.reverse()											# sort desc
		mail_list = []													# sort by field 'seconds'
		for mail in sort_list:
			mail_list.append(mail[1])									# recreate mail_list
		return mail_list


	def format_header(self, field, content):							# format sender, date, subject etc.
		if field == 'sender':
			try:
				sender_real, sender_addr = email.utils.parseaddr(content) # get the two parts of the sender
				sender_real = self.convert(sender_real)
				sender_addr = self.convert(sender_addr)
				sender = (sender_real, sender_addr)						# create decoded tupel
			except:
				sender = ('','Error: cannot format sender')

			sender_format = self.cfg.get('general', 'sender_format')
			if sender_format == '1' and sender[0] != '':				# real sender name if not empty
				sender = sender_real
			else:
				sender = sender_addr
			return sender

		if field == 'date':
			try:
				parsed_date = email.utils.parsedate_tz(content)			# make a 10-tupel (UTC)
				seconds = email.utils.mktime_tz(parsed_date)			# convert 10-tupel to seconds incl. timezone shift
				tupel = time.localtime(seconds)							# convert seconds to tupel
				datetime = time.strftime('%Y.%m.%d %X', tupel)			# convert tupel to string
			except:
				print 'Error: cannot format date.'
				datetime = time.strftime('%Y.%m.%d %X')					# take current time as "2010.12.31 13:57:04"
				seconds = time.time()									# take current time as seconds
			return datetime, seconds

		if field == 'subject':
			try:
				subject = self.convert(content)
			except:
				subject = 'Error: cannot format subject'
			return subject


	def convert(self, raw_content):										# decode and concatenate multi-coded header parts
		content = raw_content.replace('\n',' ')							# replace newline by space
		content = content.replace('?==?','?= =?')						# workaround a bug in email.header.decode_header()
		tupels = decode_header(content)									# list of (text_part, charset) tupels
		content_list = []
		for text, charset in tupels:									# iterate parts
			if charset == None: charset = 'latin-1'						# set default charset for decoding
			content_list.append(text.decode(charset, 'ignore'))			# replace non-decodable chars with 'nothing'
		decoded_content = u' '.join(content_list)						# insert blanks between parts
		decoded_content = decoded_content.strip()						# get rid of whitespace

		return decoded_content

