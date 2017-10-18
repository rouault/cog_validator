#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2017, Planet Labs
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
# *****************************************************************************

import json
import os
from flask import Flask, request as flask_request, render_template
from werkzeug.exceptions import RequestEntityTooLarge
import requests
from osgeo import gdal
import validate_cloud_optimized_geotiff
 
app = Flask(__name__)
# http://docs.aws.amazon.com/lambda/latest/dg/limits.html
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024

tmpfilename = '/tmp/cog_validator_tmp.tif'

@app.errorhandler(413)
def handle_RequestEntityTooLarge(e):
    return json.dumps({'status': 'failure', 'error': 'Maximum accepted attachment size is %d' % app.config['MAX_CONTENT_LENGTH']}), \
           413, { "Content-Type": "application/json" }

def validate(args):
    if 'url' not in args:
        return json.dumps({'status': 'failure', 'error': 'url missing'}), 400, \
               { "Content-Type": "application/json" }

    remove_tmpfile = False
    url = args.get('url')
    if 'local_filename' in args:
        ds = gdal.OpenEx(args['local_filename'], allowed_drivers = ['GTiff'])
    else:

        use_vsicurl = args.get('use_vsicurl', 'true')
        if use_vsicurl.lower() not in ('true', 'false'):
            return json.dumps({'status': 'failure', 'error': 'invalid value for use_vsicurl option. Expected true or false'}), 400, { "Content-Type": "application/json" }
        use_vsicurl = use_vsicurl.lower() == 'true'

        gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
        if use_vsicurl:
            ds = gdal.OpenEx('/vsicurl/' + url, allowed_drivers = ['GTiff'])
            if ds is None:
                f = gdal.VSIFOpenL('/vsicurl/' + url, 'rb')
                if f is None:
                    return json.dumps({'status': 'failure', 'error': 'Cannot download %s' % url}), 400, { "Content-Type": "application/json" }
                data = gdal.VSIFReadL(1,1,f)
                gdal.VSIFCloseL(f)
                if len(data) == 0:
                    error_msg = 'Cannot download %s' % url
                    gdal_error_msg = gdal.GetLastErrorMsg()
                    if gdal_error_msg == '':
                        gdal_error_msg = gdal.VSIGetLastErrorMsg()
                    if gdal_error_msg != '':
                        error_msg += ': '+ gdal_error_msg
                    return json.dumps({'status': 'failure', 'error': error_msg}), 400, { "Content-Type": "application/json" }
        else:
            try:
                r = requests.get(url)
            except Exception, e:
                return json.dumps({'status': 'failure', 'error': 'Cannot download %s' % url}), 400, { "Content-Type": "application/json" }

            remove_tmpfile = True
            f = open(tmpfilename, 'wb')
            f.write(r.content)
            f.close()
            ds = gdal.OpenEx(tmpfilename, allowed_drivers = ['GTiff'])

    if ds is None:
        return json.dumps({'status': 'failure', 'error': '%s is not a GTiff file' % url}), 400, { "Content-Type": "application/json" }
    errors, details = validate_cloud_optimized_geotiff.validate(ds)
    info = gdal.Info(ds, format = 'json')
    if 'local_filename' in args or remove_tmpfile:
        del info['files']
    info['description'] = url
    ds = None
    if remove_tmpfile:
        os.unlink(tmpfilename)

    if len(errors) == 0:
        return json.dumps({'status': 'success', 'gdal_info' : info, 'details': details}), 200, { "Content-Type": "application/json" }
    else:
        return json.dumps({'status': 'failure', 'gdal_info' : info, 'details': details, 'validation_errors': errors}), 400, { "Content-Type": "application/json" }
 
 
@app.route('/api/validate', methods=['GET', 'POST'])
def api_validate():
    if flask_request.method == 'POST':
        if flask_request.form != {}:
            if 'url' in flask_request.form and flask_request.form['url'] != '':
                args = {}
                for k in flask_request.form:
                    if k != 'local_filename':
                        args[k] = flask_request.form[k]
                return validate(args)

            if 'filename' in flask_request.form:
                url = flask_request.form['filename']
            else:
                url = 'unknown_file_name'

            if 'file_b64' not in flask_request.form:
                return json.dumps({'status': 'failure', 'error': 'Missing "file_b64" field in POSTed form data'}), 400, { "Content-Type": "application/json" }

            import base64
            b64 = flask_request.form['file_b64']
            # Need to add padding to avoid sometimes a 'invalid padding exception'
            b64 += '=='

            # FileReader::readAsDataURL() prefixes the base64 content with other stuff
            base64_marker = b64.find(';base64,')
            if base64_marker >= 0:
                b64 = b64[base64_marker + len(';base64,'):]

            try:
                decoded = base64.b64decode(b64)
            except Exception as e:
                return json.dumps({'status': 'failure', 'error': 'Invalid content for file_b64: %s' % str(e)}), 400, { "Content-Type": "application/json" }

            open(tmpfilename, 'wb').write(decoded)
        else:
            if 'file' not in flask_request.files:
                return json.dumps({'status': 'failure', 'error': 'Missing "file" field in POSTed form data'}), 400, { "Content-Type": "application/json" }
            f = flask_request.files['file']
            if f.filename == '':
                return json.dumps({'status': 'failure', 'error': 'Missing "file" field in POSTed form data'}), 400, { "Content-Type": "application/json" }
            f.save(tmpfilename)
            url = f.filename

        try:
            return validate({'local_filename': tmpfilename, 'url': url})
        finally:
            os.unlink(tmpfilename)

    else:
        args = {}
        for k in flask_request.args:
            if k != 'local_filename':
                args[k] = flask_request.args[k]
        return validate(args)

@app.route('/self_test/valid.tif', methods=['GET'])
def self_test_valid():
    return open(os.path.join(os.path.dirname(__file__), 'byte_cog_valid.tif'), 'rb').read(), 200, { "Content-Type": "image/tiff" }

@app.route('/self_test/invalid.tif', methods=['GET'])
def self_test_invalid():
    return open(os.path.join(os.path.dirname(__file__), 'byte.tif'), 'rb').read(), 200, { "Content-Type": "image/tiff" }

@app.route('/html', methods=['GET'])
def html():
    root_url = flask_request.url_root[0:-1]
    if 'AWS_API_GATEWAY_STAGE' in flask_request.environ:
        root_url += '/' + flask_request.environ['AWS_API_GATEWAY_STAGE']
    return render_template('main.html', root_url = root_url)

@app.route('/html/validate', methods=['POST'])
def html_validate():
    root_url = flask_request.url_root[0:-1]
    if 'AWS_API_GATEWAY_STAGE' in flask_request.environ:
        root_url += '/' + flask_request.environ['AWS_API_GATEWAY_STAGE']
    ret, _, _ = api_validate()
    ret = json.loads(ret)
    errors = None

    if 'url' in flask_request.form and flask_request.form['url'] != '':
        name = flask_request.form['url']
    elif 'filename' in flask_request.form and flask_request.form['filename'] != '':
        name = flask_request.form['filename']
    else:
        name = 'This'

    if 'status' in ret and ret['status'] == 'success':
        global_result = 'Validation succeeded ! %s is a valid Cloud Optimized GeoTIFF.' % name
    else:
        global_result = 'Validation failed ! %s is NOT a valid Cloud Optimized GeoTIFF.' % name
        if 'error' in ret:
            errors = [ ret['error'] ]
        elif 'validation_errors' in ret:
            errors = ret['validation_errors']
    return render_template('result.html', root_url = root_url, global_result = global_result, errors = errors)

@app.route('/health', methods=['GET'])
def health():
    return json.dumps({'status': 'OK', 'message': 'system ok'}), 200, \
               { "Content-Type": "application/json" }

# We only need this for local development.
env = os.environ
DEBUG = env.get('DEBUG', 'False')

if __name__ == '__main__':
    app.run(debug=DEBUG=="True")
