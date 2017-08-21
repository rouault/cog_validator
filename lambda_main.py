# From https://github.com/mojodna/marblecutter/blob/f5e16ea4ae0adcedaeb45d5fa66168dfe57b9232/functions/tiler/main.py
# Original work Copyright 2016 Stamen Design
# Modified work Copyright 2016-2017 Seth Fitzsimmons
# Modified work Copyright 2016 American Red Cross
# Modified work Copyright 2016-2017 Humanitarian OpenStreetMap Team
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# noqa
# coding=utf-8

import logging
import os

import awsgi
from cog_validator import app


# reset the Lambda logger
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers:
        root.removeHandler(handler)

logging.basicConfig(level=logging.INFO)


def handle(event, context): # noqa
    if 'headers' in event and isinstance(event['headers'], dict):

        # Cloudfront isn't configured to pass Host headers, so the provided Host
        # header is the API Gateway hostname
        if 'SERVER_NAME' in os.environ:
            event['headers']['Host'] = os.environ['SERVER_NAME']
        # Cloudfront drops X-Forwarded-Proto, so the value provided is from API
        # Gateway
        event['headers']['X-Forwarded-Proto'] = 'https'

    return awsgi.response(app, event, context)
