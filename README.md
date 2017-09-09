# Cloud Optimized GeoTIFF validatator

This is a standalone (Python / Flask) service that allows users to submit
GeoTIFF files (preferably by URL) and check their compliance with the
Cloud Optimized GeoTIFF (COG) specification:
https://trac.osgeo.org/gdal/wiki/CloudOptimizedGeoTIFF

This utility is also compatible of being deployed as a AWS Lambda function,
through the AWS API Gateway.

## API endpoint: /api/validate

GET request, with the following query parameters :
  * url (required): URL to the GeoTIFF file
  * use_vsicurl=true/false (optional, defaults to true): if true, the file is read using the GDAL /vsicurl/ subsystem (using HTTP GET range requests). If false, the file is locally downloaded in its entirety before being validated (note: when the service run as a AWS Lambda function, only up to 500 MB can be downloaded)

For example: /api/validate?url=http://path/to/my.tif

POST request, with a form encoded with multipart/form-data
  * file: file content as multipart attachment

POST request, with a form encoded with application/x-www-form-urlencoded
  * url (exclusive with file): URL to the GeoTIFF file
  * use_vsicurl=true/false (defaults to true). See above
  * filename (optional, recommended): file name
  * file_b64: file content as a Base64 encoded string

This later interface is mostly needed to overcome a current limitation of the AWS API Gateway interface that does not accept multipart/form-data

For all the above interfaces, the query will return a JSon document with the following keys :
  * status (required): 'success' or 'failure'
  * error (optional): error message. present when the request is invalid, or the file cannot be read
  * validation_errors (optional): array of errors. Only present if the file is a GeoTIFF file but does not comply with the COG requirements
  * gdal_info (optional): dictionary with the output of "gdalinfo -json". Only present if the file is a GeoTIFF file
  * details (optional): dictionary with file offsets of IFDs and first data block of each IFD. Only present if the file is a GeoTIFF file

## HTML endpoint: /html

The service expose a basic HTML page for users to submit their GeoTIFF files
and display the result of the validation

## AWS Lambda / API Gateway

The service can be deployed as a AWS Lamba function, accessible through the AWS API Gateway.

Running "make" will generate a cog_validator.zip that contains the Python code of this service, the Python dependencies as well as a GDAL 2.2 build. This requires Docker to be available, to generate the cog_validator_deps.zip (which contains the Python dependencies as well as a GDAL 2.2 build)

Assuming you have a AWS account with initial setup, follow the following steps to deploy the service:

- Role creation

  * Go to the AWS IAM management console
  * Click on "Roles"
  * Click on "Create new role"
  * Click on the Select button of "AWS Lambda"
  * In the Filter enter "AWSLambdaBasicExecutionRole" and check the corresponding checkbox
  * Click on "Next Step"
  * Enter "lambda_basic_execution" as role name
  * Click on "Create role"

- Lambda function creation

  * Go to the AWS Lambda management console
  * "Create function"
  * In "Select Blueprint" step, select "Author from scratch"
  * Skip Add Trigger with "Next"
  * Give a name to the function, for example "cog_validator"
  * Select "Python 2.7"  as Runtime
  * Select "Upload a .ZIP file" as "Code entry type"
  * In "Function package", click on Upload an select the generated cog_validator.zip
  * Enter "lambda_main.handle" in "Handler"
  * In "Existing role", select "lambda_basic_execution"
  * Click on Next, and Creation function to proceed on file uploading and lambda function creation
  * Edit the Configuration / Advanced settings, to increase the timeout to 5 minutes and the memory to 512 MB, and Save
  * To test everything works, in Actions dropdown list, choose "Configure test event" and enter the following payload.
```
        {
            "headers": { "Host": "foo" },
            "httpMethod": "GET",
            "queryStringParameters": { "url": "http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/byte.tif" },
            "path": "/api/validate"
        }
```

- API Gateway deployment

  * Go to the AWS API Gateway management console
  * In APIs tab, click on "Create API"
  * Enter "cog_validator" as API name
  * Click on "Create API"
  * In Resources tab, in Actions dropdown list, select "Create Resource"
  * Check the "Configure as Proxy resource" checkbox and click on "Create Resource"
  * In the "/{proxy+} - ANY - Setup" form that is now displayed, keep the "Lambda Function Proxy" integration type
  * Select the appropriate Lambda region (the one in which you created the Lambda function in the above steps)
  * In "Lambda Function" entry, type "cog_validator" 
  * Click on "Save" and confirm that you add permission to the API Gateway to invoke your Lambda function
  * To test everything works, click on the TEST icon
    * A new form is displayed. Select GET as method
    * In Path entry, enter "/api/validate"
    * In "Query strings" entry, enter "url=http://svn.osgeo.org/gdal/trunk/autotest/gcore/data/byte.tif"
    * In "Headers" entry, enter "Host: foo"
    * Click on Test. A JSon document should be displayed (with validation errors)
  * In Resources tab, in Actions dropdown list, select "Deploy API"
  * In Deployment stage, select "New stage"
  * Enter "prod" as stage name
  * Click on Deploy
  * A new form is displayed with an invoke URL like https://some_value_here.execute-api.eu-central-1.amazonaws.com/prod
  * Copy-paste it in your browser and add "/html" at the end. A HTML page "Cloud optimized GeoTIFF validator" should now be displayed !

## Development

GDAL 2.2 with its Python (2.7) bindings must be installed, as well as the Python
flask and requests modules.

A basic self test is available with the ./test.sh script

## Credits

The following resources have served as inspiration for AWS Lamba and API Gateway deployment
  * https://medium.com/@mojodna/slimming-down-lambda-deployment-zips-b3f6083a1dff
  * https://github.com/mojodna/marblecutter-tools
  * http://www.perrygeo.com/running-python-with-compiled-code-on-aws-lambda.html
