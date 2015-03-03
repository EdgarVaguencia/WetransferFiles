from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from urlparse import urlparse, parse_qs
import requests, sys, json, re, getopt, sys

DOWNLOAD_URL_PARAMS_PREFIX = "downloads/"
CHUNK_SIZE = 1024
succes = None

# Create your views here.
@csrf_protect
def home(request):
	link = None
	if request.method == 'POST':
		link = request.POST['link']
		downloadFile(link)

	return render_to_response(
    'index.html',
    context_instance = RequestContext(request)
  )

def downloadFile(argv):
	try:
		opts, args = getopt.getopt(argv, "u:h", ['url', 'help'])
		url = None
		for opt, arg in opts:
			if opt in ('-u', '--url'):
				url = arg
			if opt in ('-h', '--help'):
				usage()

		if len(argv) == 0:
			usage()

		if argv[0].find('http') == 0:
			url = argv[0]

		if not url:
			url = argv
			#usage()

		url = extract_url_redirection(url)
		[file_id, recipient_id, security_hash] = extract_params(url)
		download(file_id, recipient_id, security_hash)

	except getopt.GetoptError:
		usage()
		sys.exit(2)

def extract_url_redirection(url):
	"""
	Follow the url redirection if necesary
	"""
	return requests.get(url).url

def extract_params(url):
	"""
		Extracts params from url
	"""
	params = url.split(DOWNLOAD_URL_PARAMS_PREFIX)[1].split('/')
	[file_id, recipient_id, security_hash] = ['', '', '']
	if len(params) > 2:
		#The url is similar to https://www.wetransfer.com/downloads/XXXXXXXXXX/YYYYYYYYY/ZZZZZZZZ
		[file_id, recipient_id, security_hash] = params
	else:
		#The url is similar to https://www.wetransfer.com/downloads/XXXXXXXXXX/ZZZZZZZZ
		#In this case we have no recipient_id
		[file_id, security_hash] = params

	return [file_id, recipient_id, security_hash]

def download(file_id, recipient_id, security_hash):
	if recipient_id:
		url = "https://www.wetransfer.com/api/v1/transfers/{0}/download?recipient_id={1}&security_hash={2}&password=&ie=false".format(file_id, recipient_id, security_hash)
	else:
		url = "https://www.wetransfer.com/api/v1/transfers/{0}/download?recipient_id=9b208b70654952f49b0e7ab52cf39f7820150212002337&security_hash={1}&password=&ie=false".format(file_id, security_hash)

	print url
	r = requests.get(url)
	download_data = json.loads(r.content)

	print "Downloading {0}...".format(url)
	if download_data.has_key('direct_link'):
		content_info_string = parse_qs(urlparse(download_data['direct_link']).query)['response-content-disposition'][0]
		file_name = re.findall('filename="(.*?)"', content_info_string)[0].encode('ascii', 'ignore')
		r = requests.get(download_data['direct_link'], stream=True)
	else:
		file_name = download_data['fields']['filename']
		r = requests.post(download_data['formdata']['action'], data=download_data["fields"], stream=True)

	file_size = int(r.headers["Content-Length"])
	output_file = open('files/{0}'.format(file_name), 'wb')
	counter = 0
	for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
		if chunk:
			output_file.write(chunk)
			output_file.flush()
			sys.stdout.write('\r{0}% {1}/{2}'.format((counter * CHUNK_SIZE) * 100 / file_size, counter * CHUNK_SIZE, file_size))
			counter += 1

	sys.stdout.write('\r100% {0}/{1}\n'.format(file_size, file_size))
	output_file.close()
	print "Finished! {0}".format(file_name)
	return file_name

def usage():
	print """
	You should have a we transfer address similar to https://www.wetransfer.com/downloads/XXXXXXXXXX/YYYYYYYYY/ZZZZZZZZ
	So execute:
	python wetransfer.py -u https://www.wetransfer.com/downloads/XXXXXXXXXXXXXXXXXXXXXXXXX/YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY/ZZZZZ
	And download it! :)
	"""
	sys.exit()
	return False
