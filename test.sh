#!/bin/sh
# Self-test script

set -e

python cog_validator.py &
PYTHON_PID=$!
sleep 2

API_VALIDATE="http://127.0.0.1:5000/api/validate"

echo 'Error expected: URL missing'
ret=$(curl -s "$API_VALIDATE")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Error expected: invalid URL'
ret=$(curl -s "$API_VALIDATE?url=http://i_dont_exist.com")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Error expected: not a GeoTIFF file'
ret=$(curl -s "$API_VALIDATE?url=http://www.google.com/&use_vsicurl=false")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Error expected: not a valid COG file'
ret=$(curl -s "$API_VALIDATE?url=http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/byte.tif")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing use_vsicurl=true'
ret=$(curl -s "$API_VALIDATE?url=http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/byte.tif&use_vsicurl=true")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing a server that does not support GET range downloading'
ret=$(curl -s "$API_VALIDATE?url=http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/quad-lzw-old-style.tif")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing posting a GeoTIFF file'
ret=$(curl -s -F file=@byte_cog_valid.tif "$API_VALIDATE")
echo $ret | grep "success" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing posting a GeoTIFF file encoded in base64'
ret=$(curl -s -d "file_b64=$(base64 byte_cog_valid.tif)&filename=byte_cog_valid.tif" "$API_VALIDATE")
echo $ret | grep "success" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing posting invalid base64 content'
ret=$(curl -s -d "file_b64=x&file=byte_cog_valid.tif" "$API_VALIDATE")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'Testing the POST interface with a URL'
ret=$(curl -s -d "url=http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/byte.tif" "$API_VALIDATE")
echo $ret | grep "error" || (echo $ret; echo 'Test failure !'; kill -9 $PYTHON_PID; exit 1)
echo ''
echo ''

echo 'All tests passed !'
kill -9 $PYTHON_PID
