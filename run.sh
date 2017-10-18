#!/bin/bash

nohup gunicorn -w 2 -b 0.0.0.0:80 cog_validator:app 2>&1 > cog.log &
