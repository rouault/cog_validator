default: cog_validator.zip

cog_validator_deps.zip: Dockerfile
	docker run --rm --entrypoint cat $$(docker build --build-arg http_proxy=$(http_proxy) -q -f $< .) /tmp/task.zip > $@

cog_validator.zip: cog_validator_deps.zip awsgi.py cog_validator.py lambda_main.py templates/* byte.tif byte_cog_valid.tif
	cp $< $@
	zip -r $@ awsgi.py cog_validator.py lambda_main.py validate_cloud_optimized_geotiff.py templates byte.tif byte_cog_valid.tif
