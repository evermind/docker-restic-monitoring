#!/usr/bin/env python3

import boto3
from datetime import datetime
import time
import sys, os, socket
from socketserver import ThreadingMixIn
from http.server import HTTPServer,BaseHTTPRequestHandler
import json
import traceback

def get_env(name,default=None):
	if name in os.environ:
		return os.environ[name]
	if default is not None:
		return default
	print("Please set %s"%name)
	quit(1)

def get_s3_client():
	s3_url=get_env("S3_URL")
	aws_access_key_id=get_env("AWS_ACCESS_KEY_ID")
	aws_secret_access_key=get_env("AWS_SECRET_ACCESS_KEY")
	aws_region=get_env("AWS_REGION","us-east-1")

	session = boto3.session.Session()
	s3=session.client(
		region_name=aws_region,
		service_name='s3',
		endpoint_url=s3_url,
		aws_access_key_id=aws_access_key_id,
		aws_secret_access_key=aws_secret_access_key
		)
	return s3

def get_backup_status(bucket_name,s3=None):
	if s3 is None:
		s3=get_s3_client()

	backup={
		"name": bucket_name,
		"time": None,
		"age_hours": None,
		"error": None,
	}
	try:
		for page in s3.get_paginator('list_objects').paginate(
			Bucket=bucket_name,
			Prefix='snapshots'):
			if 'Contents' in page:
				for item in page['Contents']:
					last_modfied=item['LastModified']
					if backup['time'] is None or backup['time']<last_modfied:
						backup['time']=last_modfied
						backup['age_hours']=(datetime.now(tz=last_modfied.tzinfo)-last_modfied).total_seconds()/3600
	except Exception as e:
		backup['error']=str(e)

	return backup


def find_backups(s3=None):

	if s3 is None:
		s3=get_s3_client()

	backups=[]

	buckets=s3.list_buckets()
	for bucket in buckets['Buckets']:
		backups.append(get_backup_status(bucket['Name'],s3))
	return backups

def get_backups_json():
	try:
		ok=[]
		warn=[]
		crit=[]

		warn_age_hours=int(get_env("WARN_AGE_HOURS",36))
		crit_age_hours=int(get_env("CRIT_AGE_HOURS",72))

		for backup in find_backups():
			if backup['error']:
				crit.append("%s: %s"%(backup['name'],backup['error']))
			elif backup['age_hours'] is None:
				crit.append("%s (no backup)"%backup['name'])
			elif backup['age_hours']>crit_age_hours:
				crit.append("%s (%sh ago)"%(backup['name'],round(backup['age_hours'])))
			elif backup['age_hours']>warn_age_hours:
				warn.append("%s (%sh ago)"%(backup['name'],round(backup['age_hours'])))
			else:
				ok.append("%s (%sh ago)"%(backup['name'],round(backup['age_hours'])))

		status='OK'
		message=[]
		if len(crit)>0:
			status='CRITICAL'
			message.append("CRITICAL: %s"%(", ".join(crit)))
		if len(warn)>0:
			if status=='OK':
				status='WARNING'
			message.append("WARNING: %s"%(", ".join(warn)))
		if len(ok)>0:
			message.append("OK: %s"%(", ".join(ok)))

		return {
			"status": status,
			"message": " // ".join(message)
		}

	except Exception as e:
		return {
			"status": "CRITICAL",
			"message": "Unable to check backups: %s"%e
		}

# Webserver: https://gist.github.com/gnilchee/246474141cbe588eb9fb
class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

cached=None
cached_until=0
class MonRequestHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		if self.path=="/json":
			global cached_until,cached
			if cached_until<time.time():
				cached=get_backups_json()
				# cache for 30s to avoid DoS
				cached_until=time.time()+30

			self.send_response(200)
			self.send_header("Content-type", "application/json")
			self.end_headers()
			self.wfile.write(json.dumps(cached,indent=2).encode())
			return

		self.send_response(404)
		self.send_header("Content-type", "text/plain")
		self.end_headers()
		self.wfile.write("404 Not found.\n".encode())

def main():
	server = ThreadingSimpleServer(('0.0.0.0', 8080), MonRequestHandler)
	print("Starting webserver on port 8080")
	try:
		while 1:
			sys.stdout.flush()
			server.handle_request()
	except KeyboardInterrupt:
		print("\nShutting down server per users request.")

if __name__ == "__main__":
	main()
