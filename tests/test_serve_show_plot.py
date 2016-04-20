from bs4 import BeautifulSoup
from urlparse import urlparse as parse_url
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse
import sys
import os, inspect

configuration_folder = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
crosscompute_path = os.path.abspath(os.path.join(configuration_folder,'..'))
print crosscompute_path
sys.path.insert(1, crosscompute_path)

from crosscompute.configurations import get_tool_definition
from crosscompute.scripts.serve import get_app

def test_serve_show_plot():
	tool_definition = get_tool_definition(tool_folder=configuration_folder, tool_name='show-plot')
	client = Client(get_app(tool_definition), BaseResponse)	
	response = client.post('/tools/1', data=dict(point_table_path = "points.csv",point_table_x_column="x",point_table_y_column="y"))
	assert 303 == response.status_code
	result_url = parse_url(dict(response.headers)['Location']).path
	response = client.get(result_url)
	soup = BeautifulSoup(response.data)
	assert soup.find('div', id='result_properties').find('div',id='return_code_') is None